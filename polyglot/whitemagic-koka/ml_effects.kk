// ML Effects - ML Operations (PSR-008)
module ml_effects

effect ml
  fun load-model(model-id: string): bool
  fun predict(model-id: string, input: string): string

fun batch-predict(model-id: string, inputs: list<string>): <ml> list<string>
  if ml/load-model(model-id) then
    inputs.map fn(input) ml/predict(model-id, input)
  else
    []
