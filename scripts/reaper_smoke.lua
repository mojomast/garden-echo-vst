-- Run inside a private REAPER 7.80 evaluation instance. No external plugins.
-- GARDEN_ECHO_WORKSPACE must point to this checkout; stage=create or reopen.
local root = assert(os.getenv("GARDEN_ECHO_WORKSPACE"), "missing workspace")
local stage = assert(os.getenv("GARDEN_REAPER_STAGE"), "missing stage")
local results = root .. "/evidence/daw"
local project = results .. "/garden-host-smoke.rpp"
local file = assert(io.open(results .. "/" .. stage .. ".txt", "w"))
local function record(message) file:write(message .. "\n"); file:flush() end

local found = false
for index = 0, 10000 do
    local ok, name = reaper.EnumInstalledFX(index)
    if not ok then break end
    if name:find("Garden Echo", 1, true) then found = true; record("scan=" .. name); break end
end
assert(found, "REAPER VST3 scan did not find Garden Echo")

if stage == "create" then
    reaper.Main_OnCommand(40023, 0) -- New project; never add to a restored prior session.
    assert(reaper.CountTracks(0) == 0, "new project was not empty")
    reaper.InsertTrackAtIndex(0, true)
    local track = assert(reaper.GetTrack(0, 0))
    reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "Garden source", true)
    local item = assert(reaper.AddMediaItemToTrack(track))
    local take = assert(reaper.AddTakeToMediaItem(item))
    local input = root .. "/evidence/audio/leaf-chamber-dry.wav"
    local source = assert(reaper.PCM_Source_CreateFromFile(input))
    reaper.SetMediaItemTake_Source(take, source)
    reaper.SetMediaItemInfo_Value(item, "D_LENGTH", 3.5)
    local fx = reaper.TrackFX_AddByName(track, "VST3: Garden Echo", false, -1)
    assert(fx >= 0, "Garden Echo VST3 was not loaded")
    local _, name = reaper.TrackFX_GetFXName(track, fx)
    record("loaded=" .. name)
    local chosen = {}
    for parameter = 0, reaper.TrackFX_GetNumParams(track, fx) - 1 do
        local _, label = reaper.TrackFX_GetParamName(track, fx, parameter)
        record("parameter[" .. parameter .. "]=" .. label)
        if label == "Space" then reaper.TrackFX_SetParamNormalized(track, fx, parameter, 2 / 3); chosen.space = parameter end
        if label == "Wet" then reaper.TrackFX_SetParamNormalized(track, fx, parameter, 0.56); chosen.wet = parameter end
        if label == "Predelay" then reaper.TrackFX_SetParamNormalized(track, fx, parameter, 12 / 250); chosen.predelay = parameter end
    end
    assert(chosen.space and chosen.wet and chosen.predelay, "expected parameters not found")
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", results, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "garden-host-render", true)
    reaper.Main_SaveProjectEx(0, project, 0)
    record("saved=" .. project)
    reaper.TrackFX_Show(track, fx, 1) -- FX chain with native VST3 editor
    reaper.OnPlayButton()
    record("playing=" .. reaper.GetPlayState())
    local begin = reaper.time_precise()
    local function closeLater()
        if reaper.time_precise() - begin < 7 then reaper.defer(closeLater); return end
        reaper.OnStopButton()
        record("playback_stop=" .. reaper.GetPlayState())
        reaper.TrackFX_Show(track, fx, 0) -- close FX chain before quitting
        reaper.Main_SaveProjectEx(0, project, 0)
        file:close()
        reaper.Main_openProject("noprompt:" .. project)
        reaper.Main_OnCommand(40004, 0) -- quit
    end
    reaper.defer(closeLater)
elseif stage == "reopen" then
    local track = assert(reaper.GetTrack(0, 0), "track lost on reopen")
    assert(reaper.CountTrackMediaItems(track) == 1, "source item lost")
    assert(reaper.TrackFX_GetCount(track) == 1, "plugin lost on reopen")
    local _, name = reaper.TrackFX_GetFXName(track, 0)
    record("reopened=" .. name)
    local space, wet, predelay
    for parameter = 0, reaper.TrackFX_GetNumParams(track, 0) - 1 do
        local _, label = reaper.TrackFX_GetParamName(track, 0, parameter)
        local value = reaper.TrackFX_GetParamNormalized(track, 0, parameter)
        if label == "Space" then space = value end
        if label == "Wet" then wet = value end
        if label == "Predelay" then predelay = value end
    end
    assert(space and space > 0.62 and space < 0.71, "space parameter not restored")
    assert(wet and wet > 0.54 and wet < 0.58, "wet parameter not restored")
    assert(predelay and predelay > 0.045 and predelay < 0.052, "predelay not restored")
    record(string.format("state_space=%.5f wet=%.5f predelay=%.5f", space, wet, predelay))
    file:close()
    reaper.Main_OnCommand(40004, 0)
else
    error("unsupported stage")
end
