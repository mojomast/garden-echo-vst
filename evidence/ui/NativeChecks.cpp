#include "PluginEditor.h"
#include "StudyCatalog.h"
#include <SelectedStudies.h>
#include <iostream>
#include <stdexcept>

namespace
{
void require (bool condition, const char* message)
{
    if (! condition) throw std::runtime_error (message);
}

void checkBounds (juce::Component& parent)
{
    for (auto* child : parent.getChildren())
    {
        if (! child->isVisible()) continue;
        // Internal viewport content deliberately extends beyond its viewport.
        if (dynamic_cast<juce::Viewport*> (&parent) != nullptr) continue;
        require (parent.getLocalBounds().contains (child->getBounds()),
                 ("Visible child outside parent: " + child->getName()).toRawUTF8());
        // JUCE's Slider and ListBox own implementation-specific children.
        if (dynamic_cast<juce::Slider*> (child) == nullptr
            && dynamic_cast<juce::ListBox*> (child) == nullptr)
            checkBounds (*child);
    }
}

bool hasLabel (juce::Component& parent, const juce::String& text)
{
    if (auto* l = dynamic_cast<juce::Label*> (&parent))
        if (l->isVisible() && l->getText().contains (text)) return true;
    for (auto* child : parent.getChildren())
        if (hasLabel (*child, text)) return true;
    return false;
}

template <typename T> T* findChild (juce::Component& parent)
{
    if (auto* result = dynamic_cast<T*> (&parent)) return result;
    for (auto* child : parent.getChildren())
        if (auto* result = findChild<T> (*child)) return result;
    return nullptr;
}

juce::Component* findTitle (juce::Component& parent, const juce::String& title)
{
    if (parent.getTitle() == title) return &parent;
    for (auto* child : parent.getChildren())
        if (auto* found = findTitle (*child, title)) return found;
    return nullptr;
}
}

int main()
{
    juce::ScopedJuceInitialiser_GUI gui;
    try
    {
        garden::EchoProcessor processor;
        garden::EchoEditor editor (processor);
        for (size_t i = 0; i < garden::studyCatalog::entries.size(); ++i)
            require (juce::String (garden::studyCatalog::entries[i].id) == garden::EffectCore::presets[i].id,
                     "StudyCatalog canonical identity drift");
        const std::array<const char*, 4> mixIds {"wet", "predelay", "trim", "bypass"};
        std::array<float, 4> initialMix {};
        for (size_t i = 0; i < mixIds.size(); ++i)
            initialMix[i] = processor.parameters.getRawParameterValue (mixIds[i])->load();
        require (processor.selectedStudy() == 0 && processor.selectedSpace() == 0, "First run is not Leaf");
        auto* study = processor.parameters.getParameter ("study");
        auto* space = processor.parameters.getParameter ("space");
        auto* list = findChild<juce::ListBox> (editor);
        require (list != nullptr, "Browser list missing");
        auto* model = list->getListBoxModel();
        std::vector<int> expected {0, 0, 0};
        for (size_t i = 0; i < garden::selection::allowed.size(); ++i)
            if (garden::selection::allowed[i]) expected.push_back (static_cast<int> (i) + 1);
        expected.push_back (0);
        require (model != nullptr && model->getNumRows() == static_cast<int> (expected.size()), "Expected all allowed musical sounds and diagnostic");
        // The unfiltered complete catalog is canonical musical order, then diagnostic.
        for (int row = 0; row < static_cast<int> (expected.size()); ++row)
        {
            list->selectRow (row);
            model->returnKeyPressed (row);
            if (row < 3)
                require (processor.selectedStudy() == 0 && processor.selectedSpace() == row, "Space row mapping drift");
            else if (row + 1 < static_cast<int> (expected.size()))
                require (processor.selectedStudy() == expected[static_cast<size_t> (row)], "Study row mapping drift");
            else
                require (processor.selectedStudy() == 0 && processor.selectedSpace() == 3, "Diagnostic row mapping drift");
        }
        auto* search = findChild<juce::TextEditor> (editor);
        require (search != nullptr, "Search missing");
        auto* browser = dynamic_cast<juce::Button*> (findTitle (editor, "Sound browser"));
        require (browser != nullptr, "Browser toggle missing");
        auto showBrowser = [&] (bool open) { browser->setToggleState (open, juce::dontSendNotification); browser->onClick(); };
        auto* category = findChild<juce::ComboBox> (editor);
        require (category != nullptr, "Categories missing");
        for (const auto pair : { juce::Point<int> (20, 3), {21, static_cast<int> (expected.size()) - 4}, {22, 1} })
        {
            category->setSelectedId (pair.x, juce::dontSendNotification);
            category->onChange();
            require (model->getNumRows() == pair.y, "Top-level category inventory wrong");
            require (processor.selectedStudy() == 0 && processor.selectedSpace() == 3, "View-only category changed sound");
        }
        category->setSelectedId (1, juce::dontSendNotification);
        category->onChange();
        study->setValueNotifyingHost (study->convertTo0to1 (11.0f));
        search->setText ("prism", false);
        if (search->onTextChange) search->onTextChange();
        require (model->getNumRows() == 1, "Search did not match canonical Prism / recalled hidden Prism");
        model->returnKeyPressed (0);
        require (processor.selectedStudy() == 11, "Filtered row mapped by row index rather than canonical value");
        study->setValueNotifyingHost (study->convertTo0to1 (2.0f));
        require (search->getText() == "prism", "Automation disrupted search state");
        showBrowser (false);
        study->setValueNotifyingHost (study->convertTo0to1 (11.0f));
        require (! list->isVisible() && search->getText() == "prism", "Automation opened browser or cleared search");
        showBrowser (true);
        require (search->getText() == "prism", "Browser reopen lost search state");
        search->setText ("zzzz-no-matching-sound", false);
        if (search->onTextChange) search->onTextChange();
        require (model->getNumRows() == 0, "No-results state is not empty");
        model->returnKeyPressed (-1);
        require (processor.selectedStudy() == 11, "Empty browser Enter changed sound");
        search->setText ("", false);
        if (search->onTextChange) search->onTextChange();
        // Reproduce JUCE's real callback order: selectedRowsChanged precedes
        // listBoxItemClicked. Hidden Amber must not shift a later Steps click.
        study->setValueNotifyingHost (study->convertTo0to1 (3.0f));
        int stepsRow = -1;
        for (int row = 0; row < model->getNumRows(); ++row)
            if (model->getNameForRow (row).startsWith ("Steps Rhythmic Taps")) stepsRow = row;
        require (stepsRow >= 0, "Steps missing from test catalog");
        list->selectRow (stepsRow);
        require (processor.selectedStudy() == 3, "Browser cursor changed sound before activation");
        const auto now = juce::Time::getCurrentTime();
        const juce::MouseEvent event (juce::Desktop::getInstance().getMainMouseSource(), {}, {},
            1.0f, 0.0f, 0.0f, 0.0f, 0.0f, list, list, now, {}, now, 1, false);
        model->listBoxItemClicked (stepsRow, event);
        require (processor.selectedStudy() == 12, "Mouse callback shifted canonical selection after recalled row removal");
        model->listBoxItemDoubleClicked (stepsRow, event);
        require (processor.selectedStudy() == 12, "Double-click reactivated a stale row index");
        for (const auto size : { juce::Point<int> (710, 645), {900, 730}, {1280, 1000} })
        {
            editor.setSize (size.x, size.y);
            showBrowser (size.x >= 860);
            study->setValueNotifyingHost (study->convertTo0to1 (0.0f));
            space->setValueNotifyingHost (space->convertTo0to1 (0.0f));
            list->scrollToEnsureRowIsOnscreen (0);
            checkBounds (editor);
            const auto snapshot = editor.createComponentSnapshot (editor.getLocalBounds());
            require (snapshot.getWidth() == size.x && snapshot.getHeight() == size.y, "Native editor snapshot dimensions mismatch");
            const auto file = juce::File::getCurrentWorkingDirectory().getChildFile (
                "evidence/ui/component-" + juce::String (garden::selection::enabled ? "shortlist-" : "")
                + juce::String (size.x) + "x" + juce::String (size.y) + ".png");
            auto output = file.createOutputStream();
            require (output != nullptr, "Cannot write native editor snapshot");
            output->setPosition (0);
            output->truncate();
            require (juce::PNGImageFormat().writeImageToStream (snapshot, *output), "Native snapshot encode failed");
            for (int canonical = 0; canonical <= 12; ++canonical)
            {
                study->setValueNotifyingHost (study->convertTo0to1 (static_cast<float> (canonical)));
                require (processor.selectedStudy() == canonical, "Canonical study mismatch");
                if (canonical > 0)
                    require (hasLabel (editor, garden::EffectCore::presets[static_cast<size_t> (canonical - 1)].name), "Host recall detail not synchronized");
                const char* controlNames[] = {"TIME", "FEEDBACK", "COLOUR", "MOTION"};
                for (size_t i = 0; i < 4; ++i)
                {
                    auto* control = findTitle (editor, controlNames[i]);
                    const bool expectedVisible = canonical > 0
                        && garden::studyCatalog::entries[static_cast<size_t> (canonical - 1)].applicable[i];
                    require (control != nullptr && control->isVisible() == expectedVisible, "Inert study control applicability drift");
                }
                checkBounds (editor);
                showBrowser (true);
                checkBounds (editor);
                showBrowser (false);
                checkBounds (editor);
            }
            study->setValueNotifyingHost (study->convertTo0to1 (0.0f));
            for (int canonical = 0; canonical <= 3; ++canonical)
            {
                space->setValueNotifyingHost (space->convertTo0to1 (static_cast<float> (canonical)));
                require (processor.selectedSpace() == canonical, "Canonical space mismatch");
                checkBounds (editor);
            }
        }
        for (size_t i = 0; i < mixIds.size(); ++i)
            require (processor.parameters.getRawParameterValue (mixIds[i])->load() == initialMix[i], "Selection changed a persistent mix parameter");
        std::cout << "PASS: first-run Leaf; Enter for all allowed choices; filtered Prism; empty Enter; view-only categories; recalled-row mouse/double-click regression; automation preserves search state and does not open browser; canonical host writes 0..12 / 0..3 and heading; visible bounds with browser open/closed at all three sizes; persistent mix unchanged.\n";
        std::cout << "LIMIT: this base check does not validate screen-reader output or rendered text glyph clipping.\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
