# HMI command controls

`ignition/build_controls.py` generates `Controls.components.json` from the
Perspective event body in `command_action.py`. Paste the component JSON onto
the FeederOverview root in Designer. The panel is at (16,790), size 680×220;
the view default size is 800×1040. Save the project to the Gateway.

The CODESYS_Local OPC connection must have Read Only disabled; monitoring tags
can remain read-only because commands use explicit OPC writes. The initial
read-only connection rejected writes with Bad_ReadOnly; the user changed the
connection setting before the successful acceptance tests below.

The two buttons execute Gateway scripts. A signed-in Perspective session is
required; Designer authentication is separate. Current lab policy permits any
authenticated project user, without a separate operator role. This is a local
demonstration policy, not a production authorization design.

The script checks tag quality, ACTIVE heartbeat, existing requests and the
direction's permissives. It writes only the explicitly allowlisted Open or Close
OPC command node through `CODESYS_Local`; monitoring tags remain read-only.
The PLC retains final interlock authority. A Gateway-wide lock serializes HMI
requests. After six seconds, a finally block clears the requested command.
Browser disconnection does not control cleanup. The PLC independently clears
both requests after seven seconds of a continuously active request.

The PLC duration guard is implemented in Heartbeat after PLC_PRG in the 20 ms
MainTask. Cmd_CB_Open and Cmd_CB_Close are VAR_INPUT members so Heartbeat can
clear them. OPC symbol names remain the same. Outputs recompute the next scan.

## Acceptance status — September 24, 2026

- Controls project compiled and deployed with boot application update.
- Live PLC timeout test: an ordinary CODESYS write set Cmd_CB_Close true.
  SQL observed Cmd_CB_Close and Out_CB_Close rise at 1790263586984 and fall at
  1790263593988 UTC Unix milliseconds (7.004 seconds between samples).
  No Gateway button initiated this specific test. Final commands/outputs false.
- Unsigned Perspective session: Request CLOSE displayed “Sign in before issuing
  a command.” No new PLC command was issued by that click.
- Seven mocked command-script tests and six heartbeat tests pass.
- Signed-in Request CLOSE: command and output rose at 1790265895633 and fell at
  1790265901647 (6.014 seconds between samples), all Good quality.
- Simulated lockout active from 1790265984769 through 1790266034803: HMI displayed
  “Close blocked by PLC conditions.” No new close command/output transition.
- Signed-in Request OPEN with open indication false: command/output rose at
  1790266047816 and fell at 1790266053819 (6.003 seconds). Alarm activated at
  1790266052820, then cleared when the request ended. HMI waiting and cleared
  states were observed; the brief active-alarm screen state was not captured.
- Open indication restored true at 1790266085912. Final PLC RUN, heartbeat ACTIVE,
  lockout false, both commands/outputs false, and close permissive true.
- SQL and HMI validate a software lab sequence, not physical breaker movement.

## Signed-in live acceptance procedure

Use only the software PLC with no physical I/O. Sign in through Perspective's
session bar. Keep the Python collector running.

1. Healthy initial state, open indication true: Request CLOSE. Observe command
   and close output, then automatic reset. Feedback remains manual.
2. Apply simulated lockout in CODESYS. Request CLOSE; expect refusal and no output.
   Restore lockout false.
3. Set simulated open indication false. Request OPEN. Observe command/output;
   if no feedback arrives, the five-second missing-feedback alarm should activate
   before the six-second Gateway request ends. Restore open indication true.
4. Confirm both commands/outputs false and heartbeat ACTIVE. Regenerate the live
   report and compare the SQL events to observations. Record actual results.

The alarm clears when output is withdrawn; clearing is not proof of motion.
This lab does not latch a failed operation or calculate physical breaker travel time.
