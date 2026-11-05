# sample_stream

Captured samples as a filtered byte stream.

Sends the low byte of each sample as a one-byte packet and runs it through a
stream_filter, so only samples whose low byte reaches the threshold leave on
the flat AXI4-Stream master port.

## Ports

| Name | Direction | Type | Description |
| --- | --- | --- | --- |
| `clk` | in | logic | System clock. |
| `rst` | in | logic | Synchronous active-high reset. |
| `enable` | in | logic | Filtering is on while high. |
| `threshold` | in | logic(7:0) | Smallest low-byte value that lets a sample through. |
| `sample_data` | in | logic(full_pkg::SAMPLE_W-1:0) | Sample and its handshake from the capture path. |
| `sample_valid` | in | logic |  |
| `sample_ready` | out | logic |  |

### AXI4-Stream Manager

| Name | Direction | Type | Description |
| --- | --- | --- | --- |
| `m_axis_tdata` | out | logic(7:0) | Forwarded bytes. |
| `m_axis_tvalid` | out | logic |  |
| `m_axis_tready` | in | logic |  |
| `m_axis_tlast` | out | logic |  |

## Instances

| Instance | Of | Kind |
| --- | --- | --- |
| `s_if` | `axis_if` | interface |
| `m_if` | `axis_if` | interface |
| `u_filter` | `stream_filter` | module |
