*** Settings ***
Library    Process
Library    String

*** Variables ***
${REPO_ROOT}    /home/joe/542_odoo_group_project

*** Keywords ***
Run Fleet Test With Arg
    [Arguments]    ${arg}
    ${result}=    Run Process    bash    -lc    cd ${REPO_ROOT} && ./run_fleet_test.sh ${arg}    stdout=PIPE    stderr=STDOUT    timeout=20 minutes
    ${clean_output}=    Replace String Using Regexp    ${result.stdout}    \\x1b\\[[0-9;]*m    ${EMPTY}
    RETURN    ${result.rc}    ${clean_output}

Run Fleet Test Without Args
    ${result}=    Run Process    bash    -lc    cd ${REPO_ROOT} && ./run_fleet_test.sh    stdout=PIPE    stderr=STDOUT    timeout=5 minutes
    ${clean_output}=    Replace String Using Regexp    ${result.stdout}    \\x1b\\[[0-9;]*m    ${EMPTY}
    RETURN    ${result.rc}    ${clean_output}

Command Should Succeed
    [Arguments]    ${rc}
    Should Be Equal As Integers    ${rc}    0

Command Should Fail
    [Arguments]    ${rc}
    Should Not Be Equal As Integers    ${rc}    0

Output Should Contain
    [Arguments]    ${output}    ${expected}
    Should Contain    ${output}    ${expected}
