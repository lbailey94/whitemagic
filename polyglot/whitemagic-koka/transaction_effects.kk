// Transaction Effects - Transaction Management (PSR-001)
module transaction_effects

effect transaction
  fun begin(): ()
  fun commit(): ()
  fun rollback(): ()

fun transactional(action: () -> <transaction> a): <transaction> a
  transaction/begin()
  val result = action()
  transaction/commit()
  result
