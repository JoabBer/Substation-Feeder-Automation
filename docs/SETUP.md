# Reproduce the software lab

Validated with CODESYS 3.5 SP22 Patch 3, Ignition 8.3.9 (Perspective trial),
Windows, and Python 3.10+. Software licensing and trial renewals remain separate.

## PLC and OPC

Follow [PLC reconstruction](../plc/README.md). In Ignition, create CODESYS_Local
for your local authenticated OPC UA endpoint. Configure certificate trust using
your own certificates. Disable the connection's Read Only option to allow HMI
commands. No account names, passwords or trusted certificates are distributed.

Browse and verify the node paths in `ignition/node-map.json` and
`ignition/heartbeat-counter-node.json`; these files contain examples from the lab.
Import `Feeder01.tags.json` and `FeederDiagnostics.tags.json` into the default
provider. The Boolean monitoring tags remain read-only. Command scripts write
only the two explicit OPC command nodes.

## Monitoring and SQL

Run `python ignition/build_monitoring.py` on the Gateway machine from your cloned
folder. It generates the ignored, machine-specific FeederMonitoring.tags.json
with that clone's absolute spool directory. The Gateway service account needs
write access to `analytics/live`. Import the generated tag file, then run:

```powershell
python analytics/live_logger.py --watch
```

In a second terminal, run `python analytics/live_report.py`. See
[LIVE.md](../analytics/LIVE.md) for health checks and retention limitations.

## HMI

Create Perspective project SubstationFeederLab and a coordinate view named
FeederOverview with size 800×1040. Copy the JSON array in
`ignition/FeederOverview.all-components.json` and paste it onto the empty root
container in Designer. Map page `/` to that view and save. The companion
`FeederOverview.view.json` is the assembled view source, not a full Gateway backup.

Sign into the Perspective session separately from the Gateway/Designer. The
portable view uses clearer static ready text and a supervisory-control header;
these wording improvements do not alter command logic. See
[HMI acceptance](HMI-controls.md) for tests and the local lab authorization policy.

No Gateway backup, runtime passwords, native historian database or Seeq connection
is included. The simulated Python demo can run without CODESYS or Ignition.
