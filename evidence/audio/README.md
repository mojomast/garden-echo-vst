# Recorded-source native processor renders

`*-dry.wav` is the same generated 3.5-second stereo pluck phrase for all three spaces (48 kHz, stereo 24-bit PCM). Each `*-wet.wav` is that phrase rendered through the recorded-v1 embedded kernel in the native JUCE `EchoProcessor`, with wet 0.56, predelay 12 ms and output trim −3 dB in 256-frame blocks. These are local creative variations of **one** archived simulator trajectory and explicit impulse render, not three independent Atlas jobs or room measurements.

`garden-echo-demo.flac` losslessly concatenates the Leaf Chamber, Moss Arcade and Rain Canopy wet files in that order (10.5 seconds). The REAPER host-rendered Rain Canopy example is in `../daw/garden-host-render.wav` and is independent of these direct processor proof files. See the native checks log and recorded-source audit for scope and provenance.
