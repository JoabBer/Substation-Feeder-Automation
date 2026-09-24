PROGRAM PLC_PRG
VAR



    {attribute 'symbol' := 'readwrite'}
    Mode_Remote             : BOOL := TRUE;
    {attribute 'symbol' := 'readwrite'}
    Sts_DC_Healthy          : BOOL := TRUE;
    {attribute 'symbol' := 'readwrite'}
    Sts_Protection_Healthy  : BOOL := TRUE;
    {attribute 'symbol' := 'readwrite'}
    Sts_CB_Open             : BOOL := TRUE;
    {attribute 'symbol' := 'readwrite'}
    Sts_BusDS_Closed        : BOOL := TRUE;
    {attribute 'symbol' := 'readwrite'}
    Sts_LineDS_Closed       : BOOL := TRUE;
    {attribute 'symbol' := 'readwrite'}
    Sts_GroundDS_Open       : BOOL := TRUE;
    {attribute 'symbol' := 'readwrite'}
    Sts_Lockout86           : BOOL := FALSE;

    {attribute 'symbol' := 'read'}
    Perm_CB_Close           : BOOL := FALSE;
    {attribute 'symbol' := 'read'}
    Out_CB_Close            : BOOL := FALSE;
    {attribute 'symbol' := 'read'}
    Out_CB_Open             : BOOL := FALSE;
END_VAR
VAR_INPUT
    {attribute 'symbol' := 'readwrite'}
	Cmd_CB_Close            : BOOL := FALSE;
    {attribute 'symbol' := 'readwrite'}
    Cmd_CB_Open             : BOOL := FALSE;
END_VAR
