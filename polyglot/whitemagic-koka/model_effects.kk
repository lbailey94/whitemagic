// Model Effects - ML Model Management (PSR-008)
module model_effects

effect models
  fun load(model-id: string): bool
  fun unload(model-id: string): ()
  fun cache-model(model-id: string): ()

fun managed-inference(model-id: string, input: string): <models> maybe<string>
  if models/load(model-id) then
    models/cache-model(model-id)
    Just(input)
  else
    Nothing
