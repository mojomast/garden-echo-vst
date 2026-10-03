#pragma once
#include "PluginProcessor.h"
#include <array>
#include <memory>
#include <vector>

namespace garden
{
// Native editor for the Garden Echo processor. The editor owns only
// presentation and the two choice parameters ("space" and "study"); it never
// derives a DSP selection from a visible list index. The browser keeps stable
// row structs that carry the canonical space index (0..3, 3 = diagnostic) or
// the canonical study value (1..12).
class EchoEditor final : public juce::AudioProcessorEditor,
                         private juce::Timer,
                         private juce::ListBoxModel
{
public:
    explicit EchoEditor (EchoProcessor&);
    ~EchoEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;
    bool keyPressed (const juce::KeyPress&) override;

private:
    // A stable browser row: canonical identity only, never a filtered position.
    struct BrowserRow
    {
        bool isStudy = false;
        int canonical = 0;   // space 0..3 (3 = diagnostic), or study 1..12
        bool recalled = false;
    };

    //==== ListBoxModel ========================================================
    int getNumRows() override;
    void paintListBoxItem (int rowNumber, juce::Graphics&, int width, int height, bool rowIsSelected) override;
    juce::String getNameForRow (int rowNumber) override;
    juce::String getTooltipForRow (int rowNumber) override;
    void listBoxItemClicked (int row, const juce::MouseEvent&) override;
    void listBoxItemDoubleClicked (int row, const juce::MouseEvent&) override;
    void returnKeyPressed (int row) override;
    void selectedRowsChanged (int row) override;

    void timerCallback() override;

    //==== Construction helpers ===============================================
    void configureLabel (juce::Label&, const juce::String& text, float size, juce::Colour,
                         juce::Justification = juce::Justification::centredLeft);
    void styleDial (juce::Slider&, juce::Label&, const juce::String& text, double defaultValue,
                    const juce::String& description);
    void buildControls();
    void buildBrowser();
    void buildAttachments();
    void buildCategoryList();

    //==== Browser / selection ================================================
    void setBrowserOpen (bool shouldBeOpen, bool moveFocus);
    void rebuildRows();
    void updateBrowserStatus();
    void syncListSelection();
    void applyRow (const BrowserRow&);
    void selectCanonicalSpace (int spaceIndex);
    void selectCanonicalStudy (int studyValue);
    void stepSelection (int delta);

    int rowForCurrentSelection() const;
    bool rowMatchesCurrentSelection (const BrowserRow&) const;
    int totalCatalogRows() const;
    juce::String rowName (const BrowserRow&) const;
    juce::String rowSubtitle (const BrowserRow&) const;
    juce::String rowSearchText (const BrowserRow&) const;

    //==== Presentation ======================================================
    void refreshPresentation();
    // Authoritative overload: the choice attachments receive the canonical
    // value from the parameter itself, which avoids a one-write lag in the
    // APVTS raw value during the same listener notification.
    void refreshPresentation (int spaceValue, int studyValue);
    void paintHeader (juce::Graphics&);
    void paintDetail (juce::Graphics&);
    void paintBrowser (juce::Graphics&);
    void paintFooter (juce::Graphics&);
    void paintStudyBand (juce::Graphics&);
    void paintTapMap (juce::Graphics&, juce::Rectangle<int>, int spaceIndex);
    void paintStudyDiagram (juce::Graphics&, juce::Rectangle<int>, int studyValue);

    EchoProcessor& processor;
    std::unique_ptr<juce::LookAndFeel_V4> look;   // scoped, destroyed after children

    std::vector<BrowserRow> rows;
    juce::StringArray familyLabels;   // catalog family facet names, in first-seen order

    juce::Label title, selectedName, selectedTag, detailTag, detailName,
                detailDescription, detailListen, detailProvenance, countLabel, emptyLabel,
                wetLabel, predelayLabel, trimLabel;
    std::array<juce::Label, 4> studyLabels;

    juce::Slider wet, predelay, trim;
    std::array<juce::Slider, 4> studyDials;

    juce::TextButton prevButton, nextButton, browserButton, clearButton, provenanceButton;
    juce::ToggleButton bypass { "Bypass" };

    juce::TextEditor search;
    juce::ComboBox categoryBox;
    juce::ListBox list;
    juce::TooltipWindow tooltips { this, 650 };

    std::unique_ptr<juce::ParameterAttachment> spaceAttachment, studyAttachment;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> wetAttachment,
        predelayAttachment, trimAttachment;
    std::array<std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment>, 4> studyAttachments;
    std::unique_ptr<juce::AudioProcessorValueTreeState::ButtonAttachment> bypassAttachment;

    juce::Rectangle<int> headerBounds, detailBounds, browserBounds, footerBounds, studyBounds, mapBounds;

    int layoutMargin = 24;
    int lastSpace = -1;
    int lastStudy = -1;
    int shownSpace = 0;
    int shownStudy = 0;
    bool browserOpen = false;
    bool provenanceOpen = false;
    bool showDetail = true;
    bool suppressListCallback = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (EchoEditor)
};
} // namespace garden
