# VoltWise submission video shot list

Use a clean browser at 1440x900 or 1920x1080. Keep browser zoom at 100%. The
five scenes are separate deterministic demonstrations; always reset between
them and never narrate them as one continuous recovery.

| Time | Exact action | Required visible evidence |
| --- | --- | --- |
| 0:00-0:15 | Open `http://127.0.0.1:5173`. If needed, click **Reset demo**. | Left-aligned Digital Home, Ready to Verify panel, command input, and all three disclosure facts. No fabricated initial verdict. |
| 0:15-0:45 | Open **Demo setup**, click **Heater failure**, close the drawer, click **Turn on & verify heater**. | Reported ON remains neutral; expected about 1,500 W; observed about 7 W; **Electrical response not verified**. |
| 0:45-1:15 | Open **Demo setup**, click **Reset demo**, choose **Recovery**, close the drawer, click **Diagnose heater** directly. | First attempt about 7 W, exactly one retry, second attempt about 1,500 W, final **RECOVERED**/verified electrical response. |
| 1:15-1:40 | Open **Demo setup**, click **Reset demo**, choose **Safety stop**, close the drawer, click **Turn on & verify heater**. | About 2,200 W, 1,900 W safety threshold, **Before cutoff**, zero retries, simulated cutoff, final heater OFF. |
| 1:40-2:05 | Open **Demo setup**, click **Reset demo**, close the drawer, click **Why is our usage higher?** | 142 kWh versus 118 kWh, +24 kWh, AC estimated 15.75 kWh, unattributed 4.65 kWh. |
| 2:05-2:30 | Expand **Technical evidence** beneath the current energy result. Slowly point to the fields without scrolling past them. | `power_explain_usage_change`, Streamable HTTP, negotiated protocol, successful structured result, and duration. |
| 2:30-2:40 | Scroll or pan back to the Digital Home heading and disclosure badges. | Product name and compact simulation/real-MCP disclosure. |

## Pre-take checks

- Start with `start-voltwise.bat`; confirm UI, API, and MCP readiness messages.
- Use **Reset demo** before the first take and after any abandoned take.
- Confirm **Connected** appears and the Technical evidence panel receives a new
  MCP trace after a command.
- Keep the command input visible where practical; avoid resizing mid-take.
- If any reading differs from the table, stop, reset, and begin a new take.
- Do not use **Turn on & verify heater** before **Diagnose heater** in Recovery.

