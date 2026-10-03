#include "PluginEditor.h"
#include "StudyCatalog.h"
#include <SelectedStudies.h>
#include <algorithm>
#include <cmath>

namespace garden
{
namespace
{
//==== Charcoal / botanical palette ============================================
const juce::Colour background  (0xff0b191b);
const juce::Colour panel       (0xff17292a);
const juce::Colour panelDeep   (0xff0e2021);
const juce::Colour panelRaised (0xff1e3534);
const juce::Colour ink         (0xffe7ead5);
const juce::Colour muted       (0xff9cae9a);
const juce::Colour gold        (0xffe6bb78);
const juce::Colour outline     (0xff38524b);
const juce::Colour leaf        (0xffb9d6a5);
const juce::Colour selectionFill (0xff2c4a3f);

// Scoped custom look and feel: rotary sliders, buttons and combo boxes get the
// charcoal botanical treatment plus an explicit keyboard focus outline.
class GardenLookAndFeel final : public juce::LookAndFeel_V4
{
public:
    GardenLookAndFeel()
    {
        setColour (juce::Slider::rotarySliderFillColourId, gold);
        setColour (juce::Slider::rotarySliderOutlineColourId, outline);
        setColour (juce::Slider::thumbColourId, gold);
        setColour (juce::Slider::textBoxTextColourId, ink);
        setColour (juce::Slider::textBoxBackgroundColourId, panelDeep);
        setColour (juce::Slider::textBoxOutlineColourId, outline);
        setColour (juce::Slider::textBoxHighlightColourId, selectionFill);
        setColour (juce::ComboBox::backgroundColourId, panelRaised);
        setColour (juce::ComboBox::textColourId, ink);
        setColour (juce::ComboBox::outlineColourId, outline);
        setColour (juce::ComboBox::arrowColourId, gold);
        setColour (juce::ComboBox::focusedOutlineColourId, gold);
        setColour (juce::ComboBox::buttonColourId, panelRaised);
        setColour (juce::PopupMenu::backgroundColourId, panel);
        setColour (juce::PopupMenu::textColourId, ink);
        setColour (juce::PopupMenu::headerTextColourId, muted);
        setColour (juce::PopupMenu::highlightedBackgroundColourId, selectionFill);
        setColour (juce::PopupMenu::highlightedTextColourId, ink);
        setColour (juce::TextButton::buttonColourId, panelRaised);
        setColour (juce::TextButton::buttonOnColourId, selectionFill);
        setColour (juce::TextButton::textColourOffId, ink);
        setColour (juce::TextButton::textColourOnId, gold);
        setColour (juce::ToggleButton::textColourId, ink);
        setColour (juce::ToggleButton::tickColourId, gold);
        setColour (juce::ToggleButton::tickDisabledColourId, muted);
        setColour (juce::TextEditor::backgroundColourId, panelRaised);
        setColour (juce::TextEditor::textColourId, ink);
        setColour (juce::TextEditor::outlineColourId, outline);
        setColour (juce::TextEditor::focusedOutlineColourId, gold);
        setColour (juce::TextEditor::highlightColourId, selectionFill);
        setColour (juce::TextEditor::highlightedTextColourId, ink);
        setColour (juce::Label::textColourId, ink);
        setColour (juce::ScrollBar::thumbColourId, muted);
        setColour (juce::ListBox::backgroundColourId, panelDeep);
        setColour (juce::ListBox::outlineColourId, outline);
    }

    void drawRotarySlider (juce::Graphics& g, int x, int y, int width, int height,
                           float sliderPos, float rotaryStartAngle, float rotaryEndAngle,
                           juce::Slider& slider) override
    {
        const auto radius = (float) juce::jmin (width, height) * 0.5f - 8.0f;
        const auto centreX = (float) x + (float) width * 0.5f;
        const auto centreY = (float) y + (float) height * 0.5f;
        const auto angle = rotaryStartAngle + sliderPos * (rotaryEndAngle - rotaryStartAngle);
        const auto enabled = slider.isEnabled();

        juce::Path track;
        track.addCentredArc (centreX, centreY, radius, radius, 0.0f,
                             rotaryStartAngle, rotaryEndAngle, true);
        g.setColour (slider.findColour (juce::Slider::rotarySliderOutlineColourId)
                         .withMultipliedAlpha (enabled ? 1.0f : 0.4f));
        g.strokePath (track, juce::PathStrokeType (4.0f, juce::PathStrokeType::curved,
                                                   juce::PathStrokeType::rounded));

        juce::Path value;
        value.addCentredArc (centreX, centreY, radius, radius, 0.0f,
                             rotaryStartAngle, angle, true);
        g.setColour (slider.findColour (juce::Slider::rotarySliderFillColourId)
                         .withMultipliedAlpha (enabled ? 1.0f : 0.4f));
        g.strokePath (value, juce::PathStrokeType (4.0f, juce::PathStrokeType::curved,
                                                   juce::PathStrokeType::rounded));

        const auto knob = radius * 0.66f;
        g.setColour (panelRaised);
        g.fillEllipse (centreX - knob, centreY - knob, knob * 2.0f, knob * 2.0f);
        g.setColour (outline);
        g.drawEllipse (centreX - knob, centreY - knob, knob * 2.0f, knob * 2.0f, 1.0f);

        const juce::Point<float> pointer (centreX + knob * std::sin (angle),
                                          centreY - knob * std::cos (angle));
        g.setColour (enabled ? gold : muted);
        g.drawLine (centreX, centreY, pointer.x, pointer.y, 2.5f);

        if (slider.hasKeyboardFocus (true))
        {
            g.setColour (gold);
            g.drawEllipse (centreX - radius - 5.0f, centreY - radius - 5.0f,
                           (radius + 5.0f) * 2.0f, (radius + 5.0f) * 2.0f, 2.0f);
        }
    }

    void drawButtonBackground (juce::Graphics& g, juce::Button& button, const juce::Colour&,
                               bool shouldDrawButtonAsHighlighted, bool shouldDrawButtonAsDown) override
    {
        auto bounds = button.getLocalBounds().toFloat().reduced (0.5f);
        const auto on = button.getToggleState();
        auto base = button.findColour (on ? juce::TextButton::buttonOnColourId
                                          : juce::TextButton::buttonColourId);
        if (! button.isEnabled()) base = base.withMultipliedAlpha (0.5f);
        else if (shouldDrawButtonAsDown) base = base.brighter (0.14f);
        else if (shouldDrawButtonAsHighlighted) base = base.brighter (0.07f);

        g.setColour (base);
        g.fillRoundedRectangle (bounds, 8.0f);
        g.setColour (on ? gold.withAlpha (0.9f) : outline);
        g.drawRoundedRectangle (bounds, 8.0f, on ? 1.6f : 1.0f);

        if (button.hasKeyboardFocus (true))
        {
            g.setColour (gold);
            g.drawRoundedRectangle (bounds.reduced (2.0f), 6.0f, 2.0f);
        }
    }

    void drawToggleButton (juce::Graphics& g, juce::ToggleButton& button,
                           bool shouldDrawButtonAsHighlighted, bool shouldDrawButtonAsDown) override
    {
        auto bounds = button.getLocalBounds().toFloat().reduced (0.5f);
        const auto on = button.getToggleState();
        auto base = on ? selectionFill : panelRaised;
        if (! button.isEnabled()) base = base.withMultipliedAlpha (0.5f);
        else if (shouldDrawButtonAsDown) base = base.brighter (0.14f);
        else if (shouldDrawButtonAsHighlighted) base = base.brighter (0.07f);

        g.setColour (base);
        g.fillRoundedRectangle (bounds, bounds.getHeight() * 0.5f);
        g.setColour (on ? gold : outline);
        g.drawRoundedRectangle (bounds, bounds.getHeight() * 0.5f, on ? 1.8f : 1.0f);
        g.setColour (button.isEnabled() ? (on ? gold : ink) : muted);
        g.setFont (juce::Font (juce::FontOptions (13.0f, juce::Font::bold)));
        g.drawText (on ? "Bypassed" : "Effect active", button.getLocalBounds(), juce::Justification::centred);

        if (button.hasKeyboardFocus (true))
        {
            g.setColour (gold);
            g.drawRoundedRectangle (bounds.reduced (2.0f),
                                    juce::jmax (2.0f, bounds.getHeight() * 0.5f - 2.0f), 2.0f);
        }
    }

    void drawComboBox (juce::Graphics& g, int width, int height, bool, int, int, int, int,
                       juce::ComboBox& box) override
    {
        auto bounds = juce::Rectangle<float> (0.5f, 0.5f, (float) width - 1.0f, (float) height - 1.0f);
        g.setColour (box.findColour (juce::ComboBox::backgroundColourId));
        g.fillRoundedRectangle (bounds, 6.0f);
        const auto focused = box.hasKeyboardFocus (true);
        g.setColour (focused ? box.findColour (juce::ComboBox::focusedOutlineColourId)
                             : box.findColour (juce::ComboBox::outlineColourId));
        g.drawRoundedRectangle (bounds, 6.0f, focused ? 2.0f : 1.0f);

        const auto ax = (float) width - 15.0f;
        const auto ay = (float) height * 0.5f;
        juce::Path arrow;
        arrow.startNewSubPath (ax - 4.0f, ay - 2.0f);
        arrow.lineTo (ax, ay + 2.5f);
        arrow.lineTo (ax + 4.0f, ay - 2.0f);
        g.setColour (box.findColour (juce::ComboBox::arrowColourId));
        g.strokePath (arrow, juce::PathStrokeType (1.6f, juce::PathStrokeType::curved,
                                                   juce::PathStrokeType::rounded));
    }

    void positionComboBoxText (juce::ComboBox& box, juce::Label& label) override
    {
        label.setBounds (8, 1, box.getWidth() - 28, box.getHeight() - 2);
        label.setFont (juce::Font (juce::FontOptions (12.5f)));
        label.setJustificationType (juce::Justification::centredLeft);
    }
};
} // namespace

//==============================================================================
EchoEditor::EchoEditor (EchoProcessor& p)
    : AudioProcessorEditor (&p), processor (p)
{
    look = std::make_unique<GardenLookAndFeel>();
    setLookAndFeel (look.get());
    setTitle ("Garden Echo");
    setDescription ("Impulse-based stereo spaces and classical DSP studies");
    setWantsKeyboardFocus (true);

    buildControls();
    buildBrowser();
    buildCategoryList();

    setResizable (true, true);
    setResizeLimits (710, 645, 1280, 1000);
    setSize (900, 730);

    buildAttachments();
    rebuildRows();
    refreshPresentation();
    setBrowserOpen (getWidth() >= 860, false);

    startTimerHz (6); // low-rate safety net for host automation / state recall
}

EchoEditor::~EchoEditor()
{
    stopTimer();
    setLookAndFeel (nullptr);
}

//==============================================================================
void EchoEditor::configureLabel (juce::Label& l, const juce::String& text, float size,
                                 juce::Colour colour, juce::Justification just)
{
    l.setText (text, juce::dontSendNotification);
    l.setFont (juce::Font (juce::FontOptions (size)));
    l.setColour (juce::Label::textColourId, colour);
    l.setColour (juce::Label::backgroundColourId, juce::Colours::transparentBlack);
    l.setColour (juce::Label::outlineColourId, juce::Colours::transparentBlack);
    l.setJustificationType (just);
    l.setInterceptsMouseClicks (false, false);
    l.setMinimumHorizontalScale (0.9f);
    addAndMakeVisible (l);
}

void EchoEditor::styleDial (juce::Slider& dial, juce::Label& caption, const juce::String& text,
                            double defaultValue, const juce::String& description)
{
    dial.setSliderStyle (juce::Slider::RotaryHorizontalVerticalDrag);
    dial.setTextBoxStyle (juce::Slider::TextBoxBelow, false, 104, 32);
    dial.setTitle (text);
    dial.setDescription (description);
    dial.setTooltip (description);
    dial.setHelpText (description);
    dial.setDoubleClickReturnValue (true, defaultValue);
    dial.setScrollWheelEnabled (true);
    dial.setWantsKeyboardFocus (true);
    addAndMakeVisible (dial);
    configureLabel (caption, text, 11.0f, ink, juce::Justification::centred);
}

void EchoEditor::buildControls()
{
    configureLabel (title, "GARDEN / ECHO", 13.0f, gold, juce::Justification::centredLeft);
    title.setFont (juce::Font (juce::FontOptions (13.0f, juce::Font::bold)));
    configureLabel (selectedName, "Leaf Chamber", 24.0f, ink, juce::Justification::centredLeft);
    selectedName.setMinimumHorizontalScale (0.55f);
    configureLabel (selectedTag, "", 11.0f, muted, juce::Justification::centredLeft);

    prevButton.setButtonText ("<");
    prevButton.setTitle ("Previous sound");
    prevButton.setDescription ("Select the previous musical sound, skipping the diagnostic kernel");
    prevButton.setTooltip (prevButton.getDescription());
    prevButton.setExplicitFocusOrder (10);
    prevButton.onClick = [this] { stepSelection (-1); };
    addAndMakeVisible (prevButton);

    nextButton.setButtonText (">");
    nextButton.setTitle ("Next sound");
    nextButton.setDescription ("Select the next musical sound, skipping the diagnostic kernel");
    nextButton.setTooltip (nextButton.getDescription());
    nextButton.setExplicitFocusOrder (11);
    nextButton.onClick = [this] { stepSelection (1); };
    addAndMakeVisible (nextButton);

    browserButton.setButtonText ("Browse");
    browserButton.setClickingTogglesState (true);
    browserButton.setTitle ("Sound browser");
    browserButton.setDescription ("Show or hide the sound browser");
    browserButton.setTooltip ("Browse and search original spaces, classical DSP studies and the diagnostic kernel");
    browserButton.setColour (juce::TextButton::buttonOnColourId, selectionFill);
    browserButton.setExplicitFocusOrder (12);
    browserButton.onClick = [this] { setBrowserOpen (browserButton.getToggleState(), true); };
    addAndMakeVisible (browserButton);

    styleDial (wet, wetLabel, "WET / DRY", 0.42,
               "Wet/dry balance: 0 is dry, 1 is fully wet. Editable; double-click resets to the default.");
    styleDial (predelay, predelayLabel, "PREDELAY", 18.0,
               "Time before the effect in milliseconds. Editable; double-click resets to the default.");
    styleDial (trim, trimLabel, "OUTPUT", 0.0,
                "Output trim in decibels. Editable; double-click resets to the default.");
    predelay.setTextValueSuffix (" ms");
    trim.setTextValueSuffix (" dB");

    bypass.setTitle ("Bypass");
    bypass.setDescription ("Crossfade smoothly to the unprocessed input");
    bypass.setTooltip (bypass.getDescription());
    bypass.setWantsKeyboardFocus (true);
    bypass.setExplicitFocusOrder (13);
    addAndMakeVisible (bypass);

    const char* const names[4] = { "TIME", "FEEDBACK", "COLOUR", "MOTION" };
    const char* const descriptions[4] = {
        "Study time: scales the delay lengths. Normalised 0 to 1, default 0.50.",
        "Study feedback: scales the repeat amount. Normalised 0 to 1, default 0.50.",
        "Study colour: opens the damping filter. Normalised 0 to 1, default 0.50.",
        "Study motion: sets modulation depth and rate. Normalised 0 to 1, default 0.50."
    };
    for (size_t i = 0; i < studyDials.size(); ++i)
        styleDial (studyDials[i], studyLabels[i], names[i], 0.5, descriptions[i]);
}

void EchoEditor::buildBrowser()
{
    search.setTitle ("Search sounds");
    search.setDescription ("Filter original spaces, classical DSP studies and the diagnostic kernel by name, family, description or alias");
    search.setTooltip (search.getDescription());
    search.setTextToShowWhenEmpty ("Search sounds...", muted);
    search.setSelectAllWhenFocused (false);
    search.setExplicitFocusOrder (1);
    search.onTextChange = [this] { rebuildRows(); };
    search.onReturnKey = [this]
    {
        if (rows.empty()) return;
        list.grabKeyboardFocus();
        list.selectRow (0, false, true);
        applyRow (rows.front());
    };
    search.onEscapeKey = [this] { setBrowserOpen (false, true); };
    addAndMakeVisible (search);

    categoryBox.setTextWhenNothingSelected ("All categories");
    categoryBox.setTitle ("Category");
    categoryBox.setDescription ("Choose Recorded Spaces, Effect Studies, Diagnostic or a study family. Filtering never changes the sound.");
    categoryBox.setTooltip (categoryBox.getDescription());
    categoryBox.setExplicitFocusOrder (2);
    categoryBox.onChange = [this] { rebuildRows(); };
    addAndMakeVisible (categoryBox);

    configureLabel (countLabel, "", 11.0f, muted, juce::Justification::centredLeft);
    configureLabel (emptyLabel, "No sounds match. Change the search or press Clear.", 12.0f, muted,
                    juce::Justification::centred);
    emptyLabel.setMinimumHorizontalScale (0.85f);

    clearButton.setButtonText ("Clear");
    clearButton.setTitle ("Clear filters");
    clearButton.setDescription ("Clear the search text and category filter");
    clearButton.setTooltip (clearButton.getDescription());
    clearButton.setExplicitFocusOrder (4);
    clearButton.onClick = [this]
    {
        search.setText (juce::String(), false);
        categoryBox.setSelectedId (1, juce::dontSendNotification);
        rebuildRows();
        if (hasKeyboardFocus (true)) search.grabKeyboardFocus();
    };
    addAndMakeVisible (clearButton);

    list.setModel (this);
    list.setRowHeight (56);
    list.setMultipleSelectionEnabled (false);
    list.setColour (juce::ListBox::backgroundColourId, panelDeep);
    list.setColour (juce::ListBox::outlineColourId, outline);
    list.setOutlineThickness (1);
    list.setTitle ("Sound list");
    list.setDescription ("Original spaces, classical DSP studies and the diagnostic kernel");
    list.setTooltip ("Arrow keys and Home/End navigate, Enter selects, Escape closes");
    list.setExplicitFocusOrder (5);
    list.setWantsKeyboardFocus (true);
    addAndMakeVisible (list);

    configureLabel (detailTag, "", 10.0f, muted, juce::Justification::centredLeft);
    configureLabel (detailName, "", 25.0f, ink, juce::Justification::centredLeft);
    detailName.setMinimumHorizontalScale (0.55f);
    configureLabel (detailDescription, "", 14.0f, ink, juce::Justification::topLeft);
    detailDescription.setMinimumHorizontalScale (0.9f);
    configureLabel (detailListen, "", 12.0f, muted, juce::Justification::topLeft);
    detailListen.setMinimumHorizontalScale (0.9f);
    configureLabel (detailProvenance, "", 11.0f, muted, juce::Justification::topLeft);
    detailProvenance.setMinimumHorizontalScale (0.9f);

    provenanceButton.setButtonText ("Provenance");
    provenanceButton.setClickingTogglesState (true);
    provenanceButton.setTitle ("Provenance details");
    provenanceButton.setDescription ("Show source and mapping details for the selected sound");
    provenanceButton.setTooltip (provenanceButton.getDescription());
    provenanceButton.setColour (juce::TextButton::buttonOnColourId, selectionFill);
    provenanceButton.setExplicitFocusOrder (6);
    provenanceButton.onClick = [this]
    {
        provenanceOpen = provenanceButton.getToggleState();
        provenanceButton.setButtonText (provenanceOpen ? "Hide details" : "Provenance");
        resized();
        repaint();
    };
    addAndMakeVisible (provenanceButton);
}

void EchoEditor::buildCategoryList()
{
    // Facet names come straight from the catalog so family corrections there
    // (for example Amber repeats, Lantern texture, Brook tone) are picked up.
    familyLabels.clear();
    for (const auto& entry : studyCatalog::entries)
        familyLabels.addIfNotAlreadyThere (juce::String (entry.familyName));

    categoryBox.clear (juce::dontSendNotification);
    categoryBox.addItem ("All categories", 1);
    categoryBox.addItem ("Recorded Spaces", 20);
    categoryBox.addItem ("Effect Studies", 21);
    categoryBox.addItem ("Diagnostic", 22);
    categoryBox.addSeparator();
    for (int i = 0; i < familyLabels.size(); ++i)
        categoryBox.addItem (familyLabels[i], i + 2);
    categoryBox.setSelectedId (1, juce::dontSendNotification);
}

void EchoEditor::buildAttachments()
{
    // Choice parameters are NOT bound through ComboBoxAttachment: the visible
    // list index is deliberately independent of the canonical value. The two
    // callbacks receive the denormalised canonical value from the parameter.
    if (auto* spaceParam = processor.parameters.getParameter ("space"))
    {
        spaceAttachment = std::make_unique<juce::ParameterAttachment> (
            *spaceParam, [this] (float v)
            {
                refreshPresentation ((int) std::lround (v), shownStudy);
            });
        spaceAttachment->sendInitialUpdate();
    }
    if (auto* studyParam = processor.parameters.getParameter ("study"))
    {
        studyAttachment = std::make_unique<juce::ParameterAttachment> (
            *studyParam, [this] (float v)
            {
                refreshPresentation (shownSpace, (int) std::lround (v));
            });
        studyAttachment->sendInitialUpdate();
    }

    wetAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment> (
        processor.parameters, "wet", wet);
    predelayAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment> (
        processor.parameters, "predelay", predelay);
    trimAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment> (
        processor.parameters, "trim", trim);
    bypassAttachment = std::make_unique<juce::AudioProcessorValueTreeState::ButtonAttachment> (
        processor.parameters, "bypass", bypass);

    const char* const ids[] = { "studyTime", "studyFeedback", "studyColour", "studyMotion" };
    for (size_t i = 0; i < studyAttachments.size(); ++i)
        studyAttachments[i] = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment> (
            processor.parameters, ids[i], studyDials[i]);
}

//==============================================================================
void EchoEditor::timerCallback()
{
    const int space = processor.selectedSpace();
    const int study = processor.selectedStudy();
    if (space != lastSpace || study != lastStudy)
        refreshPresentation(); // updates detail only, never steals focus or closes the browser
    if (browserOpen) repaint (browserBounds); // hover/focus paint only; never takes focus
}

//==============================================================================
void EchoEditor::setBrowserOpen (bool shouldBeOpen, bool moveFocus)
{
    browserOpen = shouldBeOpen;
    browserButton.setToggleState (shouldBeOpen, juce::dontSendNotification);
    if (shouldBeOpen)
        rebuildRows();
    resized();
    repaint();

    if (moveFocus && hasKeyboardFocus (true))
    {
        if (shouldBeOpen) search.grabKeyboardFocus();
        else browserButton.grabKeyboardFocus();
    }
}

void EchoEditor::rebuildRows()
{
    const int category = juce::jmax (1, categoryBox.getSelectedId());
    const bool familyFilter = category >= 2 && category < 20;
    const bool includeSpaces = category == 1 || category == 20;
    const bool includeStudies = category == 1 || category == 21 || familyFilter;
    const bool includeDiagnostic = category == 1 || category == 22;
    const int family = juce::jlimit (0, juce::jmax (0, familyLabels.size() - 1), category - 2);
    const juce::String query = search.getText().trim().toLowerCase();
    const bool hasQuery = query.isNotEmpty();

    auto matches = [&] (const BrowserRow& row)
    {
        return ! hasQuery || rowSearchText (row).containsIgnoreCase (query);
    };

    rows.clear();

    if (includeSpaces)
    {
        for (int space = 0; space < 3; ++space)
        {
            const BrowserRow row { false, space, false };
            if (matches (row)) rows.push_back (row);
        }
    }

    const int selectedStudy = shownStudy;
    for (int i = 0; i < (int) EffectCore::effectCount; ++i)
    {
        if (! includeStudies) break;
        const bool allowed = selection::allowed[(size_t) i];
        const bool recalled = ! allowed && selectedStudy == i + 1;
        if (! allowed && ! recalled) continue;
        if (familyFilter && family < familyLabels.size()
            && juce::String (studyCatalog::entries[(size_t) i].familyName) != familyLabels[family])
            continue;
        const BrowserRow row { true, i + 1, recalled };
        if (! matches (row)) continue;
        rows.push_back (row);
    }

    if (includeDiagnostic)
    {
        const BrowserRow row { false, 3, false };
        if (matches (row)) rows.push_back (row);
    }

    const juce::ScopedValueSetter<bool> suppress (suppressListCallback, true);
    list.updateContent();
    updateBrowserStatus();
    syncListSelection();
}

void EchoEditor::updateBrowserStatus()
{
    const int total = totalCatalogRows();
    if ((int) rows.size() == total)
        countLabel.setText (juce::String (total - 1) + " musical + 1 diagnostic", juce::dontSendNotification);
    else
        countLabel.setText (juce::String ((int) rows.size()) + " of " + juce::String (total) + " sounds",
                            juce::dontSendNotification);

    const bool filterActive = search.getText().isNotEmpty() || categoryBox.getSelectedId() > 1;
    list.setDescription (countLabel.getText() + ". Arrow keys and Home/End navigate; Enter or click selects. Escape closes the browser.");
    clearButton.setEnabled (filterActive);
    emptyLabel.setVisible (browserOpen && rows.empty());
    if (emptyLabel.isVisible()) emptyLabel.toFront (false);
}

void EchoEditor::syncListSelection()
{
    if (! browserOpen) return;
    const int row = rowForCurrentSelection();
    const juce::ScopedValueSetter<bool> suppress (suppressListCallback, true);
    if (row < 0) list.deselectAllRows();
    else list.selectRow (row, true, true);
}

void EchoEditor::applyRow (const BrowserRow& row)
{
    if (row.isStudy) selectCanonicalStudy (row.canonical);
    else selectCanonicalSpace (row.canonical);
}

void EchoEditor::selectCanonicalSpace (int spaceIndex)
{
    const int space = juce::jlimit (0, (int) spaces.size() - 1, spaceIndex);
    if (spaceAttachment != nullptr)
        spaceAttachment->setValueAsCompleteGesture ((float) space);
    if (studyAttachment != nullptr)
        studyAttachment->setValueAsCompleteGesture (0.0f);
    else
        refreshPresentation();
}

void EchoEditor::selectCanonicalStudy (int studyValue)
{
    const int study = juce::jlimit (1, (int) EffectCore::effectCount, studyValue);
    if (studyAttachment != nullptr)
        studyAttachment->setValueAsCompleteGesture ((float) study);
    else
        refreshPresentation();
}

void EchoEditor::stepSelection (int delta)
{
    std::vector<BrowserRow> order;
    order.reserve (16);
    for (int space = 0; space < 3; ++space)          // original spaces; diagnostic (3) skipped
        order.push_back ({ false, space, false });
    for (int i = 0; i < (int) EffectCore::effectCount; ++i)
        if (selection::allowed[(size_t) i])
            order.push_back ({ true, i + 1, false });

    const int currentStudy = shownStudy;
    if (currentStudy > 0 && ! selection::allowed[(size_t) (currentStudy - 1)])
        order.push_back ({ true, currentStudy, true });

    if (order.empty()) return;

    int position = -1;
    for (int i = 0; i < (int) order.size(); ++i)
        if (rowMatchesCurrentSelection (order[(size_t) i])) { position = i; break; }
    if (position < 0)
    {
        applyRow (delta > 0 ? order.front() : order.back());
        return;
    }

    const int count = (int) order.size();
    position = ((position + delta) % count + count) % count;
    applyRow (order[(size_t) position]);
}

int EchoEditor::rowForCurrentSelection() const
{
    for (int i = 0; i < (int) rows.size(); ++i)
        if (rowMatchesCurrentSelection (rows[(size_t) i]))
            return i;
    return -1;
}

bool EchoEditor::rowMatchesCurrentSelection (const BrowserRow& row) const
{
    if (shownStudy > 0) return row.isStudy && row.canonical == shownStudy;
    return ! row.isStudy && row.canonical == shownSpace;
}

int EchoEditor::totalCatalogRows() const
{
    int total = 4; // three original spaces + diagnostic
    for (size_t i = 0; i < EffectCore::effectCount; ++i)
        if (selection::allowed[i] || shownStudy == (int) i + 1)
            ++total;
    return total;
}

juce::String EchoEditor::rowName (const BrowserRow& row) const
{
    if (row.isStudy)
    {
        const int idx = juce::jlimit (0, (int) EffectCore::effectCount - 1, row.canonical - 1);
        return juce::String (EffectCore::presets[(size_t) idx].name);
    }
    const int idx = juce::jlimit (0, (int) spaces.size() - 1, row.canonical);
    return juce::String (spaces[(size_t) idx].name);
}

juce::String EchoEditor::rowSubtitle (const BrowserRow& row) const
{
    if (row.isStudy)
    {
        const int idx = juce::jlimit (0, (int) EffectCore::effectCount - 1, row.canonical - 1);
        juce::String text = juce::String (studyCatalog::entries[(size_t) idx].familyName);
        if (row.recalled) text = "Recalled outside shortlist / " + text;
        return text;
    }
    const int idx = juce::jlimit (0, (int) spaces.size() - 1, row.canonical);
    if (idx == 3) return "DIAGNOSTIC / not a musical sound";
    return "Recorded Space / creative kernel";
}

juce::String EchoEditor::rowSearchText (const BrowserRow& row) const
{
    if (row.isStudy)
    {
        const int idx = juce::jlimit (0, (int) EffectCore::effectCount - 1, row.canonical - 1);
        const auto& entry = studyCatalog::entries[(size_t) idx];
        return juce::String (entry.id) + " " + juce::String (entry.familyName) + " "
             + juce::String (entry.listenFor) + " " + juce::String (entry.terms) + " "
             + juce::String (EffectCore::presets[(size_t) idx].name) + " "
             + juce::String (EffectCore::presets[(size_t) idx].description);
    }
    const int idx = juce::jlimit (0, (int) spaces.size() - 1, row.canonical);
    const auto& info = spaces[(size_t) idx];
    juce::String text = juce::String (info.id) + " " + juce::String (info.name) + " "
                      + juce::String (info.description);
    text += (idx == 3) ? " diagnostic identity unit impulse alignment reference"
                       : " original garden space recorded impulse";
    return text;
}

//==============================================================================
int EchoEditor::getNumRows() { return (int) rows.size(); }

void EchoEditor::paintListBoxItem (int rowNumber, juce::Graphics& g, int width, int height,
                                   bool rowIsSelected)
{
    if (! juce::isPositiveAndBelow (rowNumber, (int) rows.size())) return;
    const auto& row = rows[(size_t) rowNumber];
    auto bounds = juce::Rectangle<float> (0.0f, 0.0f, (float) width, (float) height).reduced (2.0f, 1.5f);

    if (rowIsSelected)
    {
        g.setColour (selectionFill);
        g.fillRoundedRectangle (bounds, 8.0f);
    }
    else if (rowMatchesCurrentSelection (row))
    {
        g.setColour (selectionFill.withAlpha (0.35f));
        g.fillRoundedRectangle (bounds, 8.0f);
    }
    else if (list.isMouseOver (true)
             && list.getRowContainingPosition (list.getMouseXYRelative().x, list.getMouseXYRelative().y) == rowNumber)
    {
        g.setColour (panelRaised);
        g.fillRoundedRectangle (bounds, 8.0f);
        g.setColour (muted);
        g.drawRoundedRectangle (bounds.reduced (1.0f), 7.0f, 1.0f);
    }

    g.setColour (row.isStudy ? gold : leaf);
    g.fillRoundedRectangle (bounds.getX() + 3.0f, bounds.getY() + 9.0f, 3.0f,
                            juce::jmax (6.0f, bounds.getHeight() - 18.0f), 1.5f);

    auto text = bounds.reduced (14.0f, 5.0f);
    if (rowMatchesCurrentSelection (row))
    {
        g.setColour (gold);
        g.setFont (juce::Font (juce::FontOptions (12.0f, juce::Font::bold)));
        g.drawText (">", text.removeFromRight (14).toNearestInt(), juce::Justification::centred);
    }
    auto nameArea = text.removeFromTop (text.getHeight() * 0.54f);
    g.setColour (ink);
    g.setFont (juce::Font (juce::FontOptions (13.5f, rowIsSelected ? juce::Font::bold : juce::Font::plain)));
    g.drawFittedText (rowName (row), nameArea.toNearestInt(), juce::Justification::centredLeft, 1, 0.8f);

    g.setColour (rowIsSelected ? ink : muted);
    g.setFont (juce::Font (juce::FontOptions (11.5f)));
    g.drawFittedText (rowSubtitle (row), text.toNearestInt(), juce::Justification::topLeft, 2, 0.8f);

}

juce::String EchoEditor::getNameForRow (int rowNumber)
{
    if (! juce::isPositiveAndBelow (rowNumber, (int) rows.size())) return {};
    const auto row = rows[(size_t) rowNumber];
    return rowName (row) + (row.recalled ? " / recalled outside shortlist" : "")
         + (rowMatchesCurrentSelection (row) ? " / current sound" : "");
}

juce::String EchoEditor::getTooltipForRow (int rowNumber)
{
    if (! juce::isPositiveAndBelow (rowNumber, (int) rows.size())) return {};
    return rowName (rows[(size_t) rowNumber]) + " - " + rowSubtitle (rows[(size_t) rowNumber]);
}

void EchoEditor::listBoxItemClicked (int row, const juce::MouseEvent&)
{
    if (! juce::isPositiveAndBelow (row, (int) rows.size())) return;
    // selectedRowsChanged is navigation only. Copy the canonical identity before
    // parameter callbacks can rebuild the list (e.g. leaving a recalled row).
    const auto canonicalRow = rows[(size_t) row];
    applyRow (canonicalRow);
}

void EchoEditor::listBoxItemDoubleClicked (int, const juce::MouseEvent&)
{
    // The first click already activated its canonical identity. Its old list
    // index may now mean something else after a recalled-only row disappeared.
    setBrowserOpen (false, true);
}

void EchoEditor::returnKeyPressed (int row)
{
    if (! juce::isPositiveAndBelow (row, (int) rows.size())) return;
    applyRow (rows[(size_t) row]);
}

void EchoEditor::selectedRowsChanged (int row)
{
    if (suppressListCallback) return;
    if (! juce::isPositiveAndBelow (row, (int) rows.size())) return;
    // Arrow/Home/End move the browser cursor; Enter or a click commits. This
    // avoids re-entering JUCE's mouse selection dispatch with a changed model.
    list.repaint();
}

bool EchoEditor::keyPressed (const juce::KeyPress& key)
{
    if (key == juce::KeyPress::escapeKey && browserOpen)
    {
        setBrowserOpen (false, true);
        return true;
    }
    return false;
}

//==============================================================================
void EchoEditor::refreshPresentation()
{
    refreshPresentation (processor.selectedSpace(), processor.selectedStudy());
}

void EchoEditor::refreshPresentation (int space, int study)
{
    space = juce::jlimit (0, (int) spaces.size() - 1, space);
    study = juce::jlimit (0, (int) EffectCore::effectCount, study);
    lastSpace = space;
    lastStudy = study;
    shownSpace = space;
    shownStudy = study;

    const bool isStudy = study > 0;
    juce::String name, headerTag, tag, description, listen, provenance;

    if (isStudy)
    {
        const int idx = juce::jlimit (0, (int) EffectCore::effectCount - 1, study - 1);
        const auto& preset = EffectCore::presets[(size_t) idx];
        const auto& entry = studyCatalog::entries[(size_t) idx];
        name = juce::String (preset.name);
        headerTag = juce::String (entry.familyName);
        tag = juce::String ("EFFECT STUDY / ") + juce::String (entry.familyName);
        description = juce::String (preset.description);
        if (juce::String (entry.id) == "lantern") description = "Stereo amplitude pulses with a short echo";
        if (! selection::allowed[(size_t) idx]) headerTag += " / recalled outside shortlist";
        listen = juce::String ("Listen for: ") + juce::String (entry.listenFor);
        provenance = "Authored local classical DSP. Atlas simulator output guides bounded control mapping; no hardware render, no measured-room claim and no external processing.";
    }
    else
    {
        const int idx = juce::jlimit (0, (int) spaces.size() - 1, space);
        const auto& info = spaces[(size_t) idx];
        name = juce::String (info.name);
        if (idx == 3)
        {
            headerTag = "Diagnostic";
            tag = "DIAGNOSTIC / NOT A MUSICAL SOUND";
            listen = "Alignment reference: one positive unit tap at 0 ms in both channels. Shared mix, predelay and output still apply.";
        }
        else
        {
            headerTag = "Recorded Space";
            tag = "RECORDED SPACE / IMPULSE-DERIVED CREATIVE KERNEL";
            const char* guides[] = {
                "Listen for: spacious, separated repeats with a darker signed stereo tail.",
                "Listen for: closer reflections and a gently damped, more compact echo.",
                "Listen for: slower reflections, an inverted shape and a swapped stereo image."
            };
            listen = guides[idx];
        }
        description = juce::String (info.description);
        provenance = juce::String (info.provenance) + "\nKernel SHA-256: " + juce::String (info.sha256)
                   + (idx == 3 ? "" : "\nLocal variation of one impulse render, not a measured physical room.");
    }

    selectedName.setText (name, juce::dontSendNotification);
    selectedName.setTitle ("Selected sound");
    selectedName.setDescription (name + " / " + headerTag);
    selectedTag.setText (headerTag, juce::dontSendNotification);
    selectedTag.setDescription (headerTag);
    detailTag.setText (tag, juce::dontSendNotification);
    detailName.setText (name, juce::dontSendNotification);
    detailName.setTitle ("Selected sound");
    detailName.setDescription (description);
    detailDescription.setText (description, juce::dontSendNotification);
    detailDescription.setDescription (description);
    detailListen.setText (listen, juce::dontSendNotification);
    detailListen.setDescription (listen);
    detailListen.setTooltip (listen);
    detailListen.setTitle (isStudy ? "Listening guide" : "Listening guide and static tap map summary");
    if (! isStudy)
    {
        auto summary = listen + " Static signed tap map, not a live waveform. ";
        if (space != 3)
            for (const auto& tap : spaces[(size_t) space].taps)
                summary += juce::String (tap[0] * 1000.0f, 1) + " ms: left "
                         + juce::String (tap[1], 4) + ", right " + juce::String (tap[2], 4) + ". ";
        detailListen.setDescription (summary);
        detailListen.setTooltip (summary);
    }
    detailProvenance.setText (provenance, juce::dontSendNotification);
    detailProvenance.setDescription (provenance);

    const char* const controlDescriptions[4] = {
        "Study time: scales the delay lengths. Normalised 0 to 1, default 0.50.",
        "Study feedback: scales the repeat amount. Normalised 0 to 1, default 0.50.",
        "Study colour: opens the damping filter. Normalised 0 to 1, default 0.50.",
        "Study motion: sets modulation depth and rate. Normalised 0 to 1, default 0.50."
    };
    for (size_t i = 0; i < studyDials.size(); ++i)
    {
        const bool applicable = isStudy
            && studyCatalog::entries[(size_t) (study - 1)].applicable[i];
        studyDials[i].setVisible (applicable);   // inert controls are hidden, not faked
        studyLabels[i].setVisible (applicable);
        if (applicable)
        {
            studyDials[i].setDescription (controlDescriptions[i]);
            studyDials[i].setTooltip (juce::String (controlDescriptions[i])
                                      + " Editable; double-click resets to 0.50.");
        }
    }

    provenanceButton.setButtonText (provenanceOpen ? "Hide details" : "Provenance");

    resized();
    repaint();
    rebuildRows();
}

//==============================================================================
void EchoEditor::resized()
{
    const int w = getWidth(), h = getHeight();
    if (w <= 0 || h <= 0) return;
    layoutMargin = juce::jlimit (14, 40, w / 30);

    auto area = getLocalBounds();
    headerBounds = area.removeFromTop (92);

    auto content = area;
    const int gap = 10;
    const bool studyMode = shownStudy > 0;

    footerBounds = content.removeFromBottom (144);
    studyBounds = studyMode ? content.removeFromBottom (132) : juce::Rectangle<int>();
    content.reduce (layoutMargin, gap);

    const int mainW = juce::jmax (0, content.getWidth());
    const bool railBeside = browserOpen && mainW >= 800;
    showDetail = ! browserOpen || railBeside;

    detailBounds = {};
    browserBounds = {};
    if (browserOpen)
    {
        if (railBeside)
        {
            const int railW = juce::jlimit (220, 260, mainW / 3);
            browserBounds = content.removeFromRight (railW);
            content.removeFromRight (6);
            detailBounds = content;
        }
        else
        {
            browserBounds = content; // compact: the browser replaces the detail
        }
    }
    else
    {
        detailBounds = content;
    }

    //==== header ====
    {
        auto hb = headerBounds.reduced (layoutMargin + 20, 12);
        auto right = hb.removeFromRight (juce::jmin (300, juce::jmax (150, hb.getWidth() / 2)));
        auto left = hb;
        title.setBounds (left.removeFromTop (18));
        selectedName.setBounds (left.removeFromTop (32));
        selectedTag.setBounds (left.removeFromTop (18));
        right = right.reduced (0, 10);
        browserButton.setBounds (right.removeFromRight (juce::jmin (108, juce::jmax (58, right.getWidth() / 3))));
        right.removeFromRight (8);
        nextButton.setBounds (right.removeFromRight (38));
        right.removeFromRight (4);
        prevButton.setBounds (right.removeFromRight (38));
    }

    //==== detail ====
    detailTag.setVisible (showDetail);
    detailName.setVisible (showDetail);
    detailDescription.setVisible (showDetail && detailDescription.getText().isNotEmpty());
    detailListen.setVisible (showDetail && detailListen.getText().isNotEmpty());
    provenanceButton.setVisible (showDetail);
    detailProvenance.setVisible (showDetail && provenanceOpen);

    if (showDetail && ! detailBounds.isEmpty())
    {
        auto db = detailBounds.reduced (16, 12);
        detailTag.setBounds (db.removeFromTop (15));
        detailName.setBounds (db.removeFromTop (34));
        db.removeFromTop (1);
        detailDescription.setBounds (db.removeFromTop (juce::jmin (40, db.getHeight() / 4)));
        if (detailListen.isVisible())
            detailListen.setBounds (db.removeFromTop (juce::jmin (54, db.getHeight() / 3)));
        auto bottom = db.removeFromBottom (32);
        provenanceButton.setBounds (bottom.removeFromRight (juce::jmin (108, bottom.getWidth() / 2)));
        if (provenanceOpen)
        {
            db.removeFromBottom (4);
            detailProvenance.setBounds (db.removeFromBottom (juce::jmin (92, db.getHeight() / 2)));
        }
        mapBounds = db.reduced (0, 4);
        if (mapBounds.getHeight() < 60) mapBounds = {};
    }
    else
    {
        mapBounds = {};
        detailTag.setBounds ({});
        detailName.setBounds ({});
        detailDescription.setBounds ({});
        detailListen.setBounds ({});
        provenanceButton.setBounds ({});
        detailProvenance.setBounds ({});
    }

    //==== browser ====
    search.setVisible (browserOpen);
    categoryBox.setVisible (browserOpen);
    countLabel.setVisible (browserOpen);
    clearButton.setVisible (browserOpen);
    list.setVisible (browserOpen);
    emptyLabel.setVisible (browserOpen && rows.empty());

    if (browserOpen && ! browserBounds.isEmpty())
    {
        auto bb = browserBounds.reduced (12, 10);
        bb.removeFromTop (18); // painted title
        search.setBounds (bb.removeFromTop (36));
        bb.removeFromTop (6);
        categoryBox.setBounds (bb.removeFromTop (34));
        bb.removeFromTop (4);
        auto status = bb.removeFromTop (32);
        clearButton.setBounds (status.removeFromRight (juce::jmin (64, status.getWidth() / 3)));
        status.removeFromRight (6);
        countLabel.setBounds (status);
        bb.removeFromTop (6);
        list.setBounds (bb);
        emptyLabel.setBounds (bb.withSizeKeepingCentre (bb.getWidth(), juce::jmin (bb.getHeight(), 44)));
    }
    else
    {
        search.setBounds ({});
        categoryBox.setBounds ({});
        countLabel.setBounds ({});
        clearButton.setBounds ({});
        list.setBounds ({});
        emptyLabel.setBounds ({});
    }

    //==== persistent footer ====
    {
        auto fb = footerBounds.reduced (layoutMargin, 6);
        const int colW = juce::jmax (1, fb.getWidth() / 4);
        juce::Slider* dials[3] = { &wet, &predelay, &trim };
        juce::Label* captions[3] = { &wetLabel, &predelayLabel, &trimLabel };
        for (int i = 0; i < 3; ++i)
        {
            auto col = fb.removeFromLeft (colW);
            captions[i]->setBounds (col.removeFromBottom (18));
            dials[i]->setBounds (col);
        }
        bypass.setBounds (fb.withSizeKeepingCentre (juce::jmax (84, juce::jmin (fb.getWidth() - 20, 150)), 34));
    }

    //==== study band ====
    if (studyMode && ! studyBounds.isEmpty())
    {
        auto sb = studyBounds.reduced (layoutMargin, 6);
        sb.removeFromTop (14); // painted caption
        const int colW = juce::jmax (1, sb.getWidth() / 4);
        for (size_t i = 0; i < studyDials.size(); ++i)
        {
            auto col = sb.removeFromLeft (colW);
            studyLabels[i].setBounds (col.removeFromBottom (16));
            studyDials[i].setBounds (col);
        }
    }
    else
    {
        for (size_t i = 0; i < studyDials.size(); ++i)
        {
            studyDials[i].setBounds ({});
            studyLabels[i].setBounds ({});
        }
    }
}

//==============================================================================
void EchoEditor::paint (juce::Graphics& g)
{
    g.fillAll (background);

    paintHeader (g);
    if (showDetail) paintDetail (g);
    if (browserOpen) paintBrowser (g);
    if (shownStudy > 0) paintStudyBand (g);
    paintFooter (g);
}

void EchoEditor::paintHeader (juce::Graphics& g)
{
    auto r = headerBounds.toFloat().reduced ((float) layoutMargin, 6.0f);
    if (r.isEmpty()) return;
    g.setColour (panel);
    g.fillRoundedRectangle (r, 14.0f);
    g.setColour (outline.withAlpha (0.75f));
    g.drawRoundedRectangle (r, 14.0f, 1.0f);
    g.setColour (gold);
    g.fillRoundedRectangle (r.getX() + 11.0f, r.getY() + 12.0f, 3.0f,
                            juce::jmax (8.0f, r.getHeight() - 24.0f), 1.5f);
}

void EchoEditor::paintDetail (juce::Graphics& g)
{
    const auto r = detailBounds.toFloat();
    if (r.isEmpty()) return;
    g.setColour (panel);
    g.fillRoundedRectangle (r, 16.0f);
    g.setColour (outline.withAlpha (0.75f));
    g.drawRoundedRectangle (r, 16.0f, 1.0f);

    if (! mapBounds.isEmpty())
    {
        if (shownStudy > 0)
            paintStudyDiagram (g, mapBounds, shownStudy);
        else
            paintTapMap (g, mapBounds, shownSpace);
    }
}

void EchoEditor::paintBrowser (juce::Graphics& g)
{
    const auto r = browserBounds.toFloat();
    if (r.isEmpty()) return;
    g.setColour (panel);
    g.fillRoundedRectangle (r, 16.0f);
    g.setColour (outline.withAlpha (0.85f));
    g.drawRoundedRectangle (r, 16.0f, 1.0f);

    g.setColour (gold);
    g.setFont (juce::Font (juce::FontOptions (11.0f, juce::Font::bold)));
    g.drawText ("SOUND BROWSER", browserBounds.reduced (14, 10).removeFromTop (16),
                juce::Justification::topLeft);
    if (list.hasKeyboardFocus (true))
    {
        g.setColour (gold);
        g.drawRoundedRectangle (list.getBounds().toFloat().expanded (2.0f), 3.0f, 2.0f);
    }
}

void EchoEditor::paintFooter (juce::Graphics& g)
{
    const auto r = footerBounds.toFloat();
    if (r.isEmpty()) return;
    g.setColour (panel);
    g.fillRoundedRectangle (r, 16.0f);
    g.setColour (outline.withAlpha (0.7f));
    g.drawRoundedRectangle (r, 16.0f, 1.0f);
}

void EchoEditor::paintStudyBand (juce::Graphics& g)
{
    const auto r = studyBounds.toFloat();
    if (r.isEmpty()) return;
    g.setColour (panelRaised);
    g.fillRoundedRectangle (r, 14.0f);
    g.setColour (outline.withAlpha (0.7f));
    g.drawRoundedRectangle (r, 14.0f, 1.0f);
    g.setColour (muted);
    g.setFont (juce::Font (juce::FontOptions (10.0f, juce::Font::bold)));
    g.drawText ("STUDY CONTROLS / NORMALISED 0-1 / ONLY APPLICABLE CONTROLS ARE SHOWN",
                studyBounds.reduced (layoutMargin, 6).removeFromTop (14),
                juce::Justification::topLeft);
}

//==============================================================================
void EchoEditor::paintTapMap (juce::Graphics& g, juce::Rectangle<int> area, int spaceIndex)
{
    spaceIndex = juce::jlimit (0, (int) spaces.size() - 1, spaceIndex);
    const auto frame = area.toFloat();
    if (frame.getWidth() < 60.0f || frame.getHeight() < 50.0f) return;

    g.setColour (panelDeep);
    g.fillRoundedRectangle (frame, 10.0f);
    g.setColour (outline.withAlpha (0.6f));
    g.drawRoundedRectangle (frame, 10.0f, 1.0f);

    const float padL = 34.0f, padR = 18.0f, padT = 22.0f, padB = 20.0f;
    auto plot = frame;
    plot.setLeft (frame.getX() + padL);
    plot.setRight (frame.getRight() - padR);
    plot.setTop (frame.getY() + padT);
    plot.setBottom (frame.getBottom() - padB);
    if (plot.getWidth() < 40.0f || plot.getHeight() < 40.0f) return;

    const float midL = plot.getY() + plot.getHeight() * 0.30f;
    const float midR = plot.getY() + plot.getHeight() * 0.74f;

    g.setColour (outline.withAlpha (0.85f));
    g.drawHorizontalLine ((int) midL, plot.getX(), plot.getRight());
    g.drawHorizontalLine ((int) midR, plot.getX(), plot.getRight());
    g.setFont (juce::Font (juce::FontOptions (11.0f, juce::Font::bold)));
    g.setColour (leaf);
    g.drawText ("L", (int) frame.getX() + 6, (int) midL - 8, 20, 16, juce::Justification::centredRight);
    g.setColour (gold);
    g.drawText ("R", (int) frame.getX() + 6, (int) midR - 8, 20, 16, juce::Justification::centredRight);

    if (spaceIndex == 3)
    {
        const float x = plot.getX();
        const float unitHeight = plot.getHeight() * 0.20f;
        g.setColour (gold);
        g.fillRoundedRectangle (x - 2.5f, midL - unitHeight, 5.0f, unitHeight, 2.0f);
        g.fillRoundedRectangle (x - 2.5f, midR - unitHeight, 5.0f, unitHeight, 2.0f);
        g.setColour (muted.withAlpha (0.55f));
        for (float dx = x + 10.0f; dx < plot.getRight(); dx += 11.0f)
            g.fillRect (dx, midL - 1.0f, 5.0f, 2.0f);
        g.setColour (ink);
        g.setFont (juce::Font (juce::FontOptions (11.0f, juce::Font::bold)));
        g.drawText ("DIRECT IMPULSE / 0 ms", (int) plot.getX() + 18, (int) plot.getY(),
                    (int) plot.getWidth() - 18, 18, juce::Justification::centredLeft);
        g.setColour (muted);
        g.setFont (juce::Font (juce::FontOptions (10.0f)));
        g.drawFittedText ("Unit gain in the wet path. Shared mix, predelay and output still apply.",
                    { (int) plot.getX(), (int) plot.getBottom() + 2, (int) plot.getWidth(), 16 },
                    juce::Justification::centredLeft, 1);
        return;
    }

    float tMax = 0.7f;
    for (const auto& tap : spaces[(size_t) spaceIndex].taps) tMax = juce::jmax (tMax, tap[0]);
    tMax *= 1.12f;
    auto timeToX = [&] (float t) { return plot.getX() + plot.getWidth() * (t / tMax); };

    g.setColour (outline.withAlpha (0.35f));
    for (int i = 0; i <= 4; ++i)
    {
        const auto x = plot.getX() + plot.getWidth() * (float) i / 4.0f;
        g.drawVerticalLine ((int) x, plot.getY(), plot.getBottom());
    }
    g.setColour (muted);
    g.setFont (juce::Font (juce::FontOptions (10.0f)));
    g.drawText ("0", (int) plot.getX() - 4, (int) plot.getY() - 18, 20, 16, juce::Justification::left);
    g.drawText (juce::String (juce::roundToInt (tMax * 1000.0f)),
                (int) plot.getRight() - 30, (int) plot.getY() - 18, 30, 16, juce::Justification::right);

    const float amp = plot.getHeight() * 0.34f;
    for (const auto& tap : spaces[(size_t) spaceIndex].taps)
    {
        const float t = tap[0];
        if (t <= 0.0f) continue;
        const float x = timeToX (t);
        auto bar = [&] (float mid, float gain, juce::Colour colour)
        {
            const float len = std::abs (gain) * amp;
            if (len < 0.75f) return;
            const float y = gain >= 0.0f ? mid - len : mid;
            g.setColour (colour.withAlpha (0.92f));
            g.fillRoundedRectangle (x - 3.0f, y, 6.0f, len, 2.0f);
            g.setColour (colour.brighter (0.5f));
            g.fillEllipse (x - 2.0f, gain >= 0.0f ? y - 2.0f : y + len - 2.0f, 4.0f, 4.0f);
        };
        bar (midL, tap[1], leaf);   // true signed left gain
        bar (midR, tap[2], gold);   // true signed right gain

        g.setColour (muted);
        g.setFont (juce::Font (juce::FontOptions (9.5f)));
        g.drawText (juce::String (juce::roundToInt (t * 1000.0f)) + " ms",
                    (int) x - 26, (int) plot.getY() - 18, 52, 16, juce::Justification::centred);
    }

    g.setColour (muted);
    g.setFont (juce::Font (juce::FontOptions (10.0f)));
    g.drawFittedText ("Static signed taps / up + / down - / time in ms",
                { (int) plot.getX(), (int) plot.getBottom() + 2, (int) plot.getWidth(), 16 },
                juce::Justification::centred, 1);
}

void EchoEditor::paintStudyDiagram (juce::Graphics& g, juce::Rectangle<int> area, int studyValue)
{
    const int idx = juce::jlimit (0, (int) EffectCore::effectCount - 1, studyValue - 1);
    const juce::String family = juce::String (studyCatalog::entries[(size_t) idx].familyName);
    const auto frame = area.toFloat();
    if (frame.getWidth() < 60.0f || frame.getHeight() < 50.0f) return;

    g.setColour (panelDeep);
    g.fillRoundedRectangle (frame, 10.0f);
    g.setColour (outline.withAlpha (0.6f));
    g.drawRoundedRectangle (frame, 10.0f, 1.0f);

    auto plot = frame.reduced (16.0f, 12.0f);
    auto caption = plot.removeFromBottom (16.0f);
    g.setColour (outline.withAlpha (0.5f));
    g.drawHorizontalLine ((int) plot.getCentreY(), plot.getX(), plot.getRight());

    if (family == "Repeats & rhythm")
    {
        for (int i = 0; i < 5; ++i)
        {
            const float x = plot.getX() + 10.0f + plot.getWidth() * 0.19f * (float) i;
            const float len = plot.getHeight() * 0.42f * std::pow (0.62f, (float) i);
            const bool up = (i % 2) == 0;
            const float y0 = plot.getCentreY();
            const float y1 = up ? y0 - len : y0 + len;
            g.setColour (up ? leaf : gold);
            g.fillRoundedRectangle (x - 3.0f, juce::jmin (y0, y1), 6.0f, std::abs (y1 - y0), 2.0f);
            g.setColour (muted.withAlpha (0.5f));
            g.fillEllipse (x - 2.0f, y0 - 2.0f, 4.0f, 4.0f);
        }
    }
    else if (family == "Moving & widening")
    {
        juce::Path a, b;
        for (int i = 0; i <= 48; ++i)
        {
            const float t = (float) i / 48.0f;
            const float x = plot.getX() + t * plot.getWidth();
            const float spread = plot.getHeight() * (0.05f + 0.30f * t);
            const float yA = plot.getCentreY() + spread * std::sin (t * 6.2831853f * 1.6f);
            const float yB = plot.getCentreY() - spread * std::sin (t * 6.2831853f * 1.6f + 0.9f);
            if (i == 0) { a.startNewSubPath (x, yA); b.startNewSubPath (x, yB); }
            else { a.lineTo (x, yA); b.lineTo (x, yB); }
        }
        g.setColour (leaf);
        g.strokePath (a, juce::PathStrokeType (2.0f));
        g.setColour (gold);
        g.strokePath (b, juce::PathStrokeType (2.0f));
    }
    else if (family == "Tone & resonance")
    {
        juce::Path p;
        for (int i = 0; i <= 64; ++i)
        {
            const float t = (float) i / 64.0f;
            const float x = plot.getX() + t * plot.getWidth();
            const float y = plot.getCentreY()
                          - plot.getHeight() * 0.42f * std::exp (-3.0f * t)
                          * std::sin (t * 6.2831853f * 5.0f);
            if (i == 0) p.startNewSubPath (x, y);
            else p.lineTo (x, y);
        }
        g.setColour (gold);
        g.strokePath (p, juce::PathStrokeType (2.0f));
    }
    else
    {
        juce::Random rng (0x5eed + idx);
        for (int i = 0; i < 90; ++i)
        {
            const float x = plot.getX() + rng.nextFloat() * plot.getWidth();
            const float y = plot.getCentreY() + (rng.nextFloat() - 0.5f) * plot.getHeight() * 0.72f;
            const float s = 1.0f + rng.nextFloat() * 2.5f;
            g.setColour (muted.withAlpha (0.25f + 0.5f * rng.nextFloat()));
            g.fillEllipse (x, y, s, s);
        }
        for (int i = 0; i < 3; ++i)
        {
            const float x = plot.getX() + plot.getWidth() * (0.28f + 0.22f * (float) i);
            g.setColour (gold.withAlpha (0.7f));
            g.drawEllipse (x - 7.0f, plot.getCentreY() - 7.0f, 14.0f, 14.0f, 1.5f);
        }
    }

    g.setColour (muted);
    g.setFont (juce::Font (juce::FontOptions (10.0f, juce::Font::bold)));
    g.drawFittedText ("ILLUSTRATIVE / NOT A LIVE ANALYSER",
                caption.toNearestInt(), juce::Justification::bottomRight, 1);
}
} // namespace garden
