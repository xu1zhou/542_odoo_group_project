*** Settings ***
Resource    resources/CommonKeywords.resource

*** Test Cases ***
TestCase2 Negative Invalid Argument
    [Documentation]    Negative case: invalid test id should fail with a clear validation message.
    ${rc}    ${output}=    Run Fleet Test With Arg    test_99
    Command Should Fail    ${rc}
    Output Should Contain    ${output}    Invalid test name: test_99
    Output Should Contain    ${output}    Valid values: test_01, test_02, test_03
