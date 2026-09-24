PROGRAM Heartbeat
VAR
    {attribute 'symbol' := 'read'}
    Counter : UDINT := 0;
    PulseTimer : TON;
    CommandTimer : TON;
END_VAR

// Called after PLC_PRG in the same MainTask.
// Increment every ~500 ms. Explicit wrap avoids overflow exceptions.
PulseTimer(IN := NOT PulseTimer.Q, PT := T#500ms);
IF PulseTimer.Q THEN
    IF Counter >= UDINT#4294967295 THEN
        Counter := 0;
    ELSE
        Counter := Counter + 1;
    END_IF;
END_IF;

// Lab HMI command duration guard. This POU runs after PLC_PRG.
// Independent of browser/Gateway cleanup; outputs recompute next 20 ms scan.
CommandTimer(IN := PLC_PRG.Cmd_CB_Open OR PLC_PRG.Cmd_CB_Close, PT := T#7s);
IF CommandTimer.Q THEN
    PLC_PRG.Cmd_CB_Open := FALSE;
    PLC_PRG.Cmd_CB_Close := FALSE;
END_IF;
