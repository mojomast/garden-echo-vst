cmake_minimum_required(VERSION 3.22)
project(GardenEcho VERSION 0.2.0 LANGUAGES C CXX)

# JUCE is pinned to 8.0.15 / 91ad83ae34a81e0833b1a2b0866f54846370ae53.
# Supply that checkout or its verified corresponding-source archive.
set(JUCE_ROOT "" CACHE PATH "Path to pinned JUCE 8.0.15 checkout")
if(NOT EXISTS "${JUCE_ROOT}/CMakeLists.txt")
    message(FATAL_ERROR "Set -DJUCE_ROOT=/path/to/JUCE-8.0.15")
endif()
find_package(Python3 COMPONENTS Interpreter REQUIRED)
execute_process(COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_juce_source.py" --root "${JUCE_ROOT}"
    RESULT_VARIABLE JUCE_SOURCE_RESULT)
if(NOT JUCE_SOURCE_RESULT EQUAL 0)
    message(FATAL_ERROR "Expected verified JUCE 8.0.15 source at commit 91ad83ae34a81e0833b1a2b0866f54846370ae53")
endif()
# Rebuilds must not publish the author's or runner's absolute source paths.
# Apply before JUCE is added so its compiled modules and helpers are covered.
if(MSVC)
    add_compile_options("/utf-8" "/pathmap:${CMAKE_CURRENT_SOURCE_DIR}=/usr/src/garden-echo-vst"
                        "/pathmap:${JUCE_ROOT}=/usr/src/JUCE"
                        "/pathmap:${CMAKE_CURRENT_BINARY_DIR}=/usr/src/garden-echo-build")
else()
    add_compile_options("-ffile-prefix-map=${CMAKE_CURRENT_SOURCE_DIR}=/usr/src/garden-echo-vst"
                        "-ffile-prefix-map=${JUCE_ROOT}=/usr/src/JUCE"
                        "-ffile-prefix-map=${CMAKE_CURRENT_BINARY_DIR}=/usr/src/garden-echo-build")
endif()
set(GARDEN_SPACES_DIR "${CMAKE_CURRENT_SOURCE_DIR}/fixtures/recorded-v1" CACHE PATH
    "Immutable three-space build snapshot (use fixtures/synthetic-v1 explicitly for diagnostics)")
set(SPACE_SNAPSHOT_FILES spaces.json leaf-chamber.wav moss-arcade.wav rain-canopy.wav)
get_filename_component(SPACES_ABSOLUTE "${GARDEN_SPACES_DIR}" REALPATH)
if(SPACES_ABSOLUTE STREQUAL "${CMAKE_CURRENT_SOURCE_DIR}/fixtures/synthetic-v1")
    list(APPEND SPACE_SNAPSHOT_FILES garden-pack.json)
else()
    list(APPEND SPACE_SNAPSHOT_FILES bundle.json)
endif()
foreach(required IN LISTS SPACE_SNAPSHOT_FILES)
    if(NOT EXISTS "${GARDEN_SPACES_DIR}/${required}")
        message(FATAL_ERROR "Missing ${GARDEN_SPACES_DIR}/${required}. Supply the recorded-v1 snapshot or explicitly set -DGARDEN_SPACES_DIR=${CMAKE_CURRENT_SOURCE_DIR}/fixtures/synthetic-v1 for synthetic diagnostics.")
    endif()
endforeach()
foreach(snapshot_file IN LISTS SPACE_SNAPSHOT_FILES)
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
        "${GARDEN_SPACES_DIR}/${snapshot_file}")
endforeach()
if(EXISTS "${GARDEN_SPACES_DIR}/sources")
    file(GLOB_RECURSE GARDEN_SOURCE_FILES CONFIGURE_DEPENDS LIST_DIRECTORIES FALSE
        "${GARDEN_SPACES_DIR}/sources/*")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${GARDEN_SOURCE_FILES})
endif()
execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/make_space_header.py"
        "${GARDEN_SPACES_DIR}"
        "${CMAKE_CURRENT_BINARY_DIR}/generated/SpaceData.h"
    RESULT_VARIABLE METADATA_RESULT)
if(NOT METADATA_RESULT EQUAL 0)
    message(FATAL_ERROR "Space snapshot verification failed: ${GARDEN_SPACES_DIR}")
endif()
add_subdirectory("${JUCE_ROOT}" "${CMAKE_CURRENT_BINARY_DIR}/juce" EXCLUDE_FROM_ALL)

juce_add_binary_data(GardenKernels HEADER_NAME GardenKernels.h NAMESPACE GardenKernels
    SOURCES
        "${GARDEN_SPACES_DIR}/leaf-chamber.wav"
        "${GARDEN_SPACES_DIR}/moss-arcade.wav"
        "${GARDEN_SPACES_DIR}/rain-canopy.wav"
        fixtures/synthetic-v1/identity.wav)

juce_add_plugin(GardenEcho
    COMPANY_NAME "Moth Garden"
    BUNDLE_ID "garden.moth.echo"
    PRODUCT_NAME "Garden Echo"
    PLUGIN_NAME "Garden Echo"
    DESCRIPTION "Garden Echo — impulse-based stereo spaces"
    PLUGIN_MANUFACTURER_CODE Mgdn
    PLUGIN_CODE Gdec
    FORMATS VST3 Standalone
    VST3_CATEGORIES Fx Reverb Delay
    COPY_PLUGIN_AFTER_BUILD FALSE
    NEEDS_CURL FALSE
    NEEDS_WEB_BROWSER FALSE)

target_sources(GardenEcho PRIVATE
    src/PluginProcessor.cpp src/PluginProcessor.h
    src/PluginEditor.cpp src/PluginEditor.h)
target_include_directories(GardenEcho PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(GARDEN_SELECTION_HEADER "" CACHE FILEPATH "NON-SHIP offline owner shortlist header; empty ships all 12 studies")
if(GARDEN_SELECTION_HEADER)
    if(NOT EXISTS "${GARDEN_SELECTION_HEADER}")
        message(FATAL_ERROR "Requested owner selection header does not exist")
    endif()
    configure_file("${GARDEN_SELECTION_HEADER}" "${CMAKE_CURRENT_BINARY_DIR}/generated/SelectedStudies.h" COPYONLY)
else()
    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/generated/SelectedStudies.h"
        "#pragma once\n#include <array>\nnamespace garden::selection { inline constexpr bool enabled = false; inline constexpr const char* bankSha256 = \"\"; inline constexpr std::array<bool, 12> allowed {{ true,true,true,true,true,true,true,true,true,true,true,true }}; }\n")
endif()
target_compile_features(GardenEcho PRIVATE cxx_std_17)
target_compile_definitions(GardenEcho PUBLIC
    JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_USE_CAMERA=0
    JUCE_VST3_CAN_REPLACE_VST2=0 JUCE_REPORT_APP_USAGE=0)
target_link_libraries(GardenEcho PRIVATE
    GardenKernels
    juce::juce_audio_utils juce::juce_dsp
    juce::juce_recommended_config_flags)

enable_testing()
juce_add_console_app(EchoChecks PRODUCT_NAME "EchoChecks")
target_sources(EchoChecks PRIVATE tests/EchoChecks.cpp)
target_include_directories(EchoChecks PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_features(EchoChecks PRIVATE cxx_std_17)
target_compile_definitions(EchoChecks PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_USE_CAMERA=0)
target_link_libraries(EchoChecks PRIVATE GardenEcho GardenKernels juce::juce_audio_utils juce::juce_dsp)
add_test(NAME EchoDSP COMMAND EchoChecks)

# The audition bank is rendered through precisely the same processor linked
# into the experimental VST3; no duplicate Python approximation of its DSP.
juce_add_console_app(GardenBankRender PRODUCT_NAME "GardenBankRender")
target_sources(GardenBankRender PRIVATE tests/GardenBankRender.cpp)
target_include_directories(GardenBankRender PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_features(GardenBankRender PRIVATE cxx_std_17)
target_compile_definitions(GardenBankRender PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_USE_CAMERA=0)
target_link_libraries(GardenBankRender PRIVATE GardenEcho GardenKernels juce::juce_audio_utils juce::juce_dsp)

juce_add_console_app(EffectCoreChecks PRODUCT_NAME "EffectCoreChecks")
target_sources(EffectCoreChecks PRIVATE tests/EffectCoreChecks.cpp)
target_compile_features(EffectCoreChecks PRIVATE cxx_std_17)
target_compile_definitions(EffectCoreChecks PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_USE_CAMERA=0)
target_link_libraries(EffectCoreChecks PRIVATE juce::juce_audio_utils juce::juce_dsp)
add_test(NAME EffectCoreDSP COMMAND EffectCoreChecks)

juce_add_console_app(StateMigrationChecks PRODUCT_NAME "StateMigrationChecks")
target_sources(StateMigrationChecks PRIVATE tests/StateMigrationChecks.cpp)
target_include_directories(StateMigrationChecks PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_features(StateMigrationChecks PRIVATE cxx_std_17)
target_compile_definitions(StateMigrationChecks PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_USE_CAMERA=0)
target_link_libraries(StateMigrationChecks PRIVATE GardenEcho GardenKernels juce::juce_audio_utils juce::juce_dsp)
add_test(NAME StateMigration COMMAND StateMigrationChecks)
