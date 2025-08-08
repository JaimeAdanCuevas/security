#!/bin/bash
# sesmith
#
# System{
#    BIOS = "RMLINT.86I.00.28.D685.1305021002";
#    SVOS = "ivytown-121024-368";
#    STEP = "C1";
#    SOCKETS = "2";
#    PYTHONSV_SUT = "153893";
# }
#
echo "System{"                                   > inventory.txt
echo "  Test Information {"                     >> inventory.txt
# This is available after Cleanup Step happens on ITP within the CSV
echo "    Test Step Name=;"                     >> inventory.txt
# There are two extra fields returned with this that need to be cut out
CMD=`grep 'Workflow CL :' Hexa.Agent.log | awk -F' : ' \{'print $2'}`
echo "    Test Command Line As Run=$CMD;"       >> inventory.txt
echo "    TEST_ID=$TEST_ID;"                    >> inventory.txt
echo "    Line Number=$TEST_LineNum;"           >> inventory.txt
echo "    Rerun Index=$TEST_LineNum;"           >> inventory.txt
echo "    Test Suite=$TEST_Suite;"              >> inventory.txt
# Need to determine how and if we can get this
echo "    Test Group=;"                         >> inventory.txt
# Need to determine how and if we can get this
echo "    Debug Level=;"                        >> inventory.txt
echo "    Hardware Configuration=$TEST_Cfg;"    >> inventory.txt

echo "    Soft Configuration=;"                 >> inventory.txt
echo "    Test Station=$HexaStationName;"       >> inventory.txt
# Need to determine how and if we can get this

START_DATE=`head -1 ../Test/Hexa.Agent.log | awk -F' ' \{'print $2}`
START_TIME=`head -1 ../Test/Hexa.Agent.log | awk -F' ' \{'print $3}`
END_DATE = `tail -1 ../Test/Hexa.Agent.log | awk -F' ' \{'print $2}`
END_TIME = `tail -1 ../Test/Hexa.Agent.log | awk -F' ' \{'print $3}`


echo "    Test Stage Time=;"                    >> inventory.txt
echo "    Run Results=$TEST_Failed;"            >> inventory.txt
# Need to determine how and if we can get this
echo "    EXEC_SEED=;"                          >> inventory.txt
echo "  }"                                      >> inventory.txt

echo "  Platform Information {"                 >> inventory.txt
BIOS_REV=`grep 'BIOS Details: ' ../PreBoot/UpdateBIOS_* | awk -F': ' \{'print $2'} | awk -F' ' \{'print $2'}`
echo "    BIOS Revision=$BIOS_REV;"             >> inventory.txt
# Need to determine how and if we can get this
echo "    Microcode Patch Revision=;"           >> inventory.txt
# Need to determine how and if we can get this
echo "    ME/SPS Revision=;"                    >> inventory.txt
echo "    Execution Site=$SITE;"                >> inventory.txt
echo "    System Under Test=`hostname`;"        >> inventory.txt
# Need to determine how and if we can get this
# Can use HexaStationName=DPS3350V02A and replace the S with H
echo "    Host Machine=;"                       >> inventory.txt
# Need to determine how and if we can get this
echo "    Client(s) Used=;"                     >> inventory.txt
echo "    CPU Information {"                    >> inventory.txt
# Need to determine how and if we can get this
echo "      Stepping=;"                         >> inventory.txt
# Need to determine how and if we can get this
echo "      QDF=;"                              >> inventory.txt
# Need to determine how and if we can get this
echo "      ULT=;"                              >> inventory.txt
# Need to determine how and if we can get this
echo "      Socket Location=;"                  >> inventory.txt
# Need to determine how and if we can get this
echo "      Fuse Revision=;"                    >> inventory.txt
echo "    }"                                    >> inventory.txt
# Need to determine how and if we can get this
echo "    Num Sockets Populated=;"              >> inventory.txt
# Need to determine how and if we can get this
echo "    DIMM Population {"                    >> inventory.txt
# Need to determine how and if we can get this
echo "      Fuse Revision=;"                    >> inventory.txt
echo "    }"                                    >> inventory.txt
# Need to determine how and if we can get this
echo "    IO Population Information=;"          >> inventory.txt
# Need to determine how and if we can get this
echo "    Platform Type {"                      >> inventory.txt
# Need to determine how and if we can get this
echo "      Rework Revision=;"                  >> inventory.txt
# Need to determine how and if we can get this
echo "      PLD Revision=;"                     >> inventory.txt
# Need to determine how and if we can get this
echo "      BMC Revision=;"                     >> inventory.txt
echo "    }"                                    >> inventory.txt
echo "  }"                                      >> inventory.txt

echo "  Software Information {"                 >> inventory.txt
OSRev=`grep 'svos' SVOS4Update`
echo "    OSRev=$OSRev;"                        >> inventory.txt
PYTHONSV_REV=`grep 'Revision: ' /usr/local/python/svninfo.log | awk -F': ' \{'print $2'}`
echo "    PYTHONSV_REV=$PYTHONSV_REV;"          >> inventory.txt
# Need to determine how and if we can get this
echo "    Inventory Rev=$Val_Tools;"            >> inventory.txt
# This will be included in the Val_tools distribution and as such I'll use that
Val_Tools=`grep 'Revision: ' /usr/local/val_tools/svninfo.log | awk -F': ' \{'print $2'}`
echo "    Inventory Script Revision=;"          >> inventory.txt
CONTENT_REV=`grep 'Revision: ' SL_Content/svninfo.log | awk -F': ' \{'print $2'}`
echo "    CONTENT_REV=$CONTENT_REV;"            >> inventory.txt
ISIS_REV=`grep 'Revision: ' Isis/svninfo.log | awk -F': ' \{'print $2'}`
echo "    ISIS_REV=$ISIS_REV;"                  >> inventory.txt
TSSA_REV=`grep 'Revision: ' TargetSSARevision | awk -F': ' \{'print $2'}`
echo "    TSSA_REV=$TSSA_REV;"                  >> inventory.txt
Origami_REV=`grep 'Revision: ' /usr/local/Origami/OrigamiRevision | awk -F': ' \{'print $2'}`
echo "    Origami_REV=$Origami_REV;"            >> inventory.txt
NvmTools=`grep 'Revision: ' /usr/local/NvmTools/NvmTools.rev | awk -F': ' \{'print $2'}`
echo "    NvmTools_REV=$NvmTools;"              >> inventory.txt
Linux_RbV_Tools=`grep 'Revision: ' /usr/local/rbv/svninfo.log | awk -F': ' \{'print $2'}`
echo "    Linux_RbV_Tools=$Linux_RbV_Tools;"    >> inventory.txt
Win_RbV_Tools=`grep 'Revision: ' svninfo.log | awk -F': ' \{'print $2'}`
echo "    Win_RbV_Tools=$Win_RbV_Tools;"        >> inventory.txt
echo "    Val_Tools=$Val_Tools;"                >> inventory.txt
Runner=`grep 'Release Package: ' /runner/help/release_notes.txt | awk -F': ' \{'print $2'}` 
echo "    Runner=$Runner"                       >> inventory.txt
echo ";"                                        >> inventory.txt
echo "  }"                                      >> inventory.txt
# Need to determine how and if we can get this
echo "  FUSE_REV=;"                             >> inventory.txt
SIZE=`du -sb . | awk \{'print $1'}` # uncompressed size when inventory was run
echo "  SIZE=$SIZE;"                            >> inventory.txt
echo "}"                                        >> inventory.txt
