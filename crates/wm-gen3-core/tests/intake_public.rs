//! Exercises the real downstream API: core is compiled without `cfg(test)` here.
use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::{Class, Domain, RatifiedChannel, RecordStatus};
use wm_gen3_core::intake::{CommitDisposition, IntakeKind, IntakeRequest, OperationId};
use wm_gen3_core::ops::{ImportKind, RememberItem, Substrate};

#[test]
fn downstream_intake_requires_authority_and_preserves_committed_identity() {
    let mut nonce = [0u8; 16];
    getrandom::fill(&mut nonce).unwrap();
    let path = std::env::temp_dir().join(format!(
        "wm-gen3-public-intake-{:x}",
        u128::from_be_bytes(nonce)
    ));
    let channel = RatifiedChannel::mint("synthetic-public-issuer");
    let other = RatifiedChannel::mint("synthetic-other-issuer");
    let item = RememberItem {
        content: "Synthetic durable downstream evidence record".into(),
        source: "corpus:fixture:public-api".into(),
        kind: ImportKind::Reported,
    };
    let request;
    {
        let mut substrate = Substrate::open(&path, None, default_view()).unwrap();
        let results = substrate.remember_batch(std::slice::from_ref(&item));
        assert_eq!(
            results[0].as_ref().unwrap_err(),
            "intake authority is not installed"
        );
        assert_eq!(substrate.store().record_count().unwrap(), 0);
        assert_eq!(substrate.intake_epoch().unwrap(), 0);

        request = IntakeRequest::new(
            &channel,
            OperationId::from_bytes([19; 16]),
            substrate.intake_realm_id().unwrap(),
            0,
            0,
            IntakeKind::Reported,
            item.content.clone(),
            item.source.clone(),
        )
        .unwrap();
        assert!(
            substrate
                .remember_authorized(&other, request.clone())
                .is_err()
        );
        assert_eq!(substrate.intake_epoch().unwrap(), 0);
        let result = substrate
            .remember_authorized(&channel, request.clone())
            .unwrap();
        assert_eq!(result.disposition, CommitDisposition::Committed);
        assert_eq!(result.receipt.record_id, 0);
        assert_eq!(result.receipt.post_epoch, 1);
        let record = substrate.store().get_record(0).unwrap().unwrap();
        assert_eq!(record.domain(), Domain::Reported);
        assert_eq!(record.class(), Class::Evidence);
        assert_eq!(record.status(), RecordStatus::Persistent);
        assert_eq!(record.created_at(), 0);
        assert_eq!(record.confidence(), 1.0);
    }
    {
        let mut substrate = Substrate::open(&path, None, default_view()).unwrap();
        let retry = substrate.remember_authorized(&channel, request).unwrap();
        assert_eq!(retry.disposition, CommitDisposition::Replay);
        assert_eq!(retry.receipt.record_id, 0);
        assert_eq!(substrate.intake_epoch().unwrap(), 1);
        substrate.set_intake_authority(channel);
        let next = RememberItem {
            content: "Synthetic second downstream observation".into(),
            ..item
        };
        assert_eq!(substrate.remember_batch(&[next]), vec![Ok(1)]);
        assert_eq!(substrate.intake_epoch().unwrap(), 2);
    }
    std::fs::remove_dir_all(path).unwrap();
}
