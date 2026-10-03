-- Private final VST3 host smoke; all output is confined to the caller's directory.
local root = assert(os.getenv("GARDEN_ECHO_WORKSPACE"))
local output = assert(os.getenv("GARDEN_FINAL_OUTPUT"))
local stage = assert(os.getenv("GARDEN_REAPER_STAGE"))
local project = output .. "/final-host.rpp"
local file = assert(io.open(output .. "/reaper-" .. stage .. ".txt", "w"))
local function record(s) file:write(s .. "\n"); file:flush() end
local function finish() file:close(); reaper.Main_OnCommand(40004, 0) end

local found = false
for index = 0, 10000 do
    local ok, name = reaper.EnumInstalledFX(index)
    if not ok then break end
    if name:find("Garden Echo", 1, true) then
        record("scan=" .. name)
        found = true
        break
    end
end
assert(found, "final VST3 missing from REAPER scan")

if stage == "create" then
    reaper.Main_OnCommand(40023, 0)
    reaper.InsertTrackAtIndex(0, true)
    local track = assert(reaper.GetTrack(0, 0))
    local item = assert(reaper.AddMediaItemToTrack(track))
    local take = assert(reaper.AddTakeToMediaItem(item))
    local source = assert(reaper.PCM_Source_CreateFromFile(root .. "/evidence/audio/leaf-chamber-dry.wav"))
    reaper.SetMediaItemTake_Source(take, source)
    reaper.SetMediaItemInfo_Value(item, "D_LENGTH", 3.5)
    local fx = reaper.TrackFX_AddByName(track, "VST3: Garden Echo", false, -1)
    assert(fx >= 0, "final VST3 could not be loaded")
    local _, name = reaper.TrackFX_GetFXName(track, fx)
    record("loaded=" .. name)
    local params = {}
    for n = 0, reaper.TrackFX_GetNumParams(track, fx) - 1 do
        local _, label = reaper.TrackFX_GetParamName(track, fx, n)
        params[label] = n
        record("parameter[" .. n .. "]=" .. label)
    end
    assert(params.Space and params.Study and params.Wet and params.Predelay, "required host controls absent")
    local function choice(label, index, last)
        reaper.TrackFX_SetParamNormalized(track, fx, params[label], index / last)
        local actual = reaper.TrackFX_GetParamNormalized(track, fx, params[label])
        assert(math.abs(actual - index / last) < .005, label .. " host choice rejected")
        record(string.format("selection=%s index=%d normalized=%.5f", label, index, actual))
    end
    -- Each family is represented by an independently host-selectable study.
    for _, index in ipairs({1, 4, 7, 8}) do choice("Study", index, 12) end
    choice("Study", 0, 12)
    choice("Space", 3, 3) -- unit impulse / diagnostic
    record("diagnostic=unit-impulse")
    choice("Space", 1, 3)
    choice("Study", 4, 12) -- Petal Chorus, persisted across reopen/render
    reaper.TrackFX_SetParamNormalized(track, fx, params.Wet, .56)
    reaper.TrackFX_SetParamNormalized(track, fx, params.Predelay, 12 / 250)
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", output, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "final-host-render", true)
    reaper.Main_SaveProjectEx(0, project, 0)
    record("saved=" .. project)
    reaper.TrackFX_Show(track, fx, 1)
    local start = reaper.time_precise()
    local function closeLater()
        if reaper.time_precise() - start < 8 then reaper.defer(closeLater); return end
        reaper.TrackFX_Show(track, fx, 0)
        finish()
    end
    reaper.defer(closeLater)
elseif stage == "reopen" then
    local track = assert(reaper.GetTrack(0, 0), "saved track missing")
    assert(reaper.CountTrackMediaItems(track) == 1 and reaper.TrackFX_GetCount(track) == 1,
        "saved source or effect missing")
    local _, name = reaper.TrackFX_GetFXName(track, 0)
    record("reopened=" .. name)
    local values = {}
    for n = 0, reaper.TrackFX_GetNumParams(track, 0) - 1 do
        local _, label = reaper.TrackFX_GetParamName(track, 0, n)
        values[label] = reaper.TrackFX_GetParamNormalized(track, 0, n)
    end
    assert(values.Space and math.abs(values.Space - 1 / 3) < .005, "space restore mismatch")
    assert(values.Study and math.abs(values.Study - 4 / 12) < .005, "study restore mismatch")
    assert(values.Wet and math.abs(values.Wet - .56) < .005, "wet restore mismatch")
    assert(values.Predelay and math.abs(values.Predelay - 12 / 250) < .005,
        "predelay restore mismatch")
    record(string.format("state_space=%.5f study=%.5f wet=%.5f predelay=%.5f",
        values.Space, values.Study, values.Wet, values.Predelay))
    finish()
else
    error("unsupported stage")
end
