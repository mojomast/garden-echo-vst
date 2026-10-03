# Garden Echo — source release status

Owner approval recorded 2026-10-03: publish the VST-only source in a fresh public
repository, including the documented Atlas-derived outputs, kernels and audio
examples. This records the owner's permission confirmation; it is not an
independent legal opinion about upstream terms.

Authored code is GNU AGPLv3. JUCE 8.0.15 is used under its AGPLv3 option;
no commercial-license entitlement is claimed. Preserve the source and
third-party notices. Any distributed binary must meet corresponding-source
and other applicable license obligations.

## What is available

- Native VST3 source, embedded kernels, native DSP tests and sound inventory.
- Real native UI captures and archived audio examples with provenance.
- Build instructions for pinned JUCE 8.0.15.

## What is not claimed

- No public precompiled binary or completed contest submission yet.
- No physical listening, screen-reader or real high-DPI certification.
- No Windows, macOS, AU or older-Linux compatibility claim.
- No quantum hardware execution or quantum advantage.

The measured Linux review module requires symbols through GLIBC_2.38.
CTest 3/3 and pluginval strictness 5 passed for the recorded candidate; the
optional external Steinberg validator was not configured. See
[`VST_RELEASE_VERIFICATION.md`](../evidence/release-readiness/VST_RELEASE_VERIFICATION.md).

On 2026-10-03 a history-free native-source export was independently configured
and built with pinned JUCE and the existing Linux sysroot. CTest 3/3,
pluginval strictness 5 and inventory verification passed. Its Python suite ran
27 tests with seven explicit missing-authoring-input skips. The resulting
module SHA-256 was
`bbfaba0d86f31d36f270d020e28580239ca2eee1e54a4652d88c2e7265493564`;
maximum observed required GLIBC remained `GLIBC_2.38`. The clean-export pass
did not repeat DAW or listening tests. Documentation links were repaired after
that build; native source and embedded assets were unchanged.

Historical command logs and REAPER projects use sanitized `/workspace/...`
paths. Those paths describe earlier test layouts, not locations guaranteed to
exist on your machine; project fixtures may need path remapping before reopening.
Sanitized logs preserve test values but are not byte-identical private originals.

## Before a binary release or contest submission

1. Build and test the exact source revision; hash the entire bundle and package.
2. Provide corresponding source and required license/dependency notices.
3. Listen on named hardware and validate the intended host/platform.
4. Include the actual plugin and audio examples for Challenge 07.
5. Recheck the official rules and obtain approval of the exact submission.

The official page checked 2026-10-03 lists the virtual hackathon as
26 September–5 October (PT), winners 7 October, and judging on execution,
depth of quantum/Atlas usage and originality. An exact closing time and
pre-existing-code/AI/team eligibility remain unconfirmed.
Source: https://moth-quantum.github.io/moth-hack-sep-2026/ .
