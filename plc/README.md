# PLC source

`FeederControl.plcopen.xml` is a source export of the deployed PLC_PRG ladder
program and Heartbeat program. It excludes device accounts and connection state.
The ST files expose the declarations and heartbeat implementation for review;
the ladder body is in the PLCopen XML export.

To reconstruct in CODESYS V3.5 SP22 Patch 3:

1. Create a Standard Project with CODESYS Control Win V3 x64, for a local software lab.
2. Import the PLCopen XML programs into the Application. Avoid duplicate PLC_PRG.
3. Add the Standard library for TON if not already present.
4. Set MainTask to a 20 ms cyclic interval. Call PLC_PRG first, then Heartbeat.
5. Add Symbol Configuration with OPC UA support. Publish the 13 Boolean symbols
   and Heartbeat.Counter, respecting their source access attributes. Do not map
   this demonstration to physical I/O.
6. Build, configure your own authenticated local runtime connection and certificate
   trust, download, and start the application. Browse actual OPC node paths before
   importing Ignition tags; device naming may change the example paths.

The native local project is not published because it is an opaque engineering
container with machine-specific state. The XML export preserves editable ladder
source. Import on a clean second machine has not been independently tested.
