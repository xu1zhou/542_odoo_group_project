*** Settings ***
Resource    resources/CommonKeywords.resource

*** Test Cases ***
TestCase1 Positive Run test_01
    [Documentation]    Positive case: running test_01 should succeed and print highlighted test metadata.
    ${rc}    ${output}=    Run Fleet Test With Arg    test_01
    Command Should Succeed    ${rc}
    Output Should Contain    ${output}    Test Name: test_01
    Output Should Contain    ${output}    Test Message:
    Output Should Contain    ${output}    Result:
