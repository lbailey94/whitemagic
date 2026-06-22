// Validation Effects - Validation Operations (PSR-009)
module validation_effects

effect validation
  fun validate-rule(rule-id: string, data: string): bool
  fun get-failures(): list<string>

fun validate-all(rules: list<string>, data: string): <validation> (int, int)
  var passed := 0
  var failed := 0
  rules.foreach fn(rule)
    if validation/validate-rule(rule, data) then
      passed := passed + 1
    else
      failed := failed + 1
  (passed, failed)
