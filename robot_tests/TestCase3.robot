*** Settings ***
Resource    resources/CommonKeywords.resource

*** Test Cases ***
TestCase3 Negative Missing Argument
    [Documentation]    Negative case: missing argument should fail and print usage.
    ${rc}    ${output}=    Run Fleet Test Without Args
    Command Should Fail    ${rc}
    Output Should Contain    ${output}    Usage: ./run_fleet_test.sh test_01|test_02|test_03
