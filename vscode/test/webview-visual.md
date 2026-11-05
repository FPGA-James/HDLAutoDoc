# Checking the panel by eye

`npm test` renders real documents (`test/fixtures/*.json`, produced by `autodoc_json.py` from
`example_full`) in headless Chrome under the extension's content-security policy and checks that
every waveform, Mermaid diagram and state machine is drawn, in a light and a dark theme, and that the
waveforms are thin lines rather than filled shapes. It writes screenshots to `test/out/`; open
`sample_ctrl-dark.png` and `sample_capture-light.png` to see what the panel looks like.

Chrome is found at the usual macOS and Linux paths, or set `CHROME=/path/to/chrome`. Without
Chrome the webview tests are skipped.

To refresh a fixture after changing `autodoc_json.py`:

    python3 ../src/scripts/hdl_autodoc/autodoc_json.py --language vhdl \
        < ../example_full/src/sample_ctrl.vhd | python3 -m json.tool > test/fixtures/sample_ctrl.json
