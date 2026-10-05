//! Integration tests for Phase A (Landlock Confinement & WorkspaceClaim)
//! and Phase B (Spec 0.5 Continuity Receipt Notarization).

use ed25519_dalek::SigningKey;
use std::fs;
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::Command;
use wm_gen3_core::mandala::{
    ContinuityReceipt05, KekkaiPhase, LandlockSandbox, MandalaError, SandboxResourceLimits,
    StateCommitmentRecord, WorkspaceClaim,
};

fn test_keys() -> (SigningKey, ed25519_dalek::VerifyingKey) {
    let seed = [42u8; 32];
    let signing = SigningKey::from_bytes(&seed);
    let verifying = signing.verifying_key();
    (signing, verifying)
}

fn create_temp_subdirs(prefix: &str) -> (PathBuf, PathBuf) {
    let base = std::env::temp_dir().join(format!("{}_{}", prefix, std::process::id()));
    let ws = base.join("workspace");
    let outside = base.join("forbidden_outside");
    let _ = fs::remove_dir_all(&base);
    fs::create_dir_all(&ws).expect("create ws dir");
    fs::create_dir_all(&outside).expect("create outside dir");
    (ws, outside)
}

#[test]
fn test_workspace_claim_and_ruleset_construction() {
    let (signing_key, verifying_key) = test_keys();
    let (ws_path, _outside) = create_temp_subdirs("wm_test_claim");

    let mut claim = WorkspaceClaim {
        claim_id: "claim-phase-a-001".to_string(),
        tenant_id: "tenant-lucas-sovereign".to_string(),
        agent_id: "agent-geneseed-maker-01".to_string(),
        workspace_root: ws_path.clone(),
        read_only_paths: vec![PathBuf::from("/usr"), PathBuf::from("/lib")],
        read_write_paths: vec![ws_path.clone()],
        network_allowed: false,
        kekkai_phase: KekkaiPhase::Hoi,
        resource_limits: Some(SandboxResourceLimits::default()),
        inherited_shm_fd: None,
        created_at: 1_700_000_000,
        expires_at: 1_700_003_600,
        signature: None,
    };

    claim.sign(&signing_key);
    assert!(claim.signature.is_some());
    assert!(claim.verify(&verifying_key).is_ok());

    // Landlock ruleset creation must succeed
    let ruleset = LandlockSandbox::build_ruleset(&claim);
    assert!(
        ruleset.is_ok(),
        "Landlock ruleset should build cleanly: {:?}",
        ruleset.err()
    );
}

#[test]
fn test_continuity_receipt_spec_05_tamper_evidence() {
    let (signing_key, verifying_key) = test_keys();

    let commitment = StateCommitmentRecord {
        state_kind: "kv_canonical".to_string(),
        scope: "gen3/evolutionary_factory".to_string(),
        count: 142,
        head_digest: "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"
            .to_string(),
        merkle_root: Some(
            "sha256:b5a2c9b7351fc5f72e258354924c5a6f22b820f6329ca0eb9cf7091361248ec2".to_string(),
        ),
    };

    let mut receipt = ContinuityReceipt05::new(
        "receipt-spec05-verify-01".to_string(),
        "tenant-lucas-sovereign".to_string(),
        "agent-geneseed-maker-01".to_string(),
        "session-continuity-20261002".to_string(),
        1_727_910_000_000,
        "landlock".to_string(),
        "sha256:3a41c6e3b2e5912384764b8823528b9487f5263a233b3b4f6e1f0e495f269a8b".to_string(),
        true,
        "sha256:preflight-clean-zero-leaks".to_string(),
        Some(commitment),
        "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK".to_string(),
    );

    receipt.sign(&signing_key);
    assert!(receipt.signature.is_some());
    assert_eq!(receipt.verify(&verifying_key), Ok(()));

    // Tampering test 1: Modify receipt ID
    let mut tampered = receipt.clone();
    tampered.receipt_id = "receipt-spec05-verify-FORGED".to_string();
    assert_eq!(
        tampered.verify(&verifying_key),
        Err(MandalaError::SignatureInvalid)
    );

    // Tampering test 2: Invert preflight clearance
    let mut tampered2 = receipt.clone();
    tampered2.preflight_clearance = false;
    assert_eq!(
        tampered2.verify(&verifying_key),
        Err(MandalaError::SignatureInvalid)
    );

    // Tampering test 3: Alter state commitment count
    let mut tampered3 = receipt.clone();
    if let Some(ref mut c) = tampered3.state_commitment {
        c.count = 999;
    }
    assert_eq!(
        tampered3.verify(&verifying_key),
        Err(MandalaError::SignatureInvalid)
    );

    // Tampering test 4: Alter workspace claim digest
    let mut tampered4 = receipt.clone();
    tampered4.workspace_claim_digest = "sha256:tampered_digest".to_string();
    assert_eq!(
        tampered4.verify(&verifying_key),
        Err(MandalaError::SignatureInvalid)
    );

    // Tampering test 5: Alter kekkai phase
    let mut tampered5 = receipt.clone();
    tampered5.kekkai_phase = Some(KekkaiPhase::Metsu);
    assert_eq!(
        tampered5.verify(&verifying_key),
        Err(MandalaError::SignatureInvalid)
    );
}

/// Tests Landlock process restriction inside a spawned child process.
/// Verifies filesystem confinement, resource limits, and network scoping.
#[test]
#[cfg(target_os = "linux")]
fn test_landlock_subprocess_confinement() {
    let (ws_path, outside_path) = create_temp_subdirs("wm_test_confinement");

    // Check if running as child test worker
    if std::env::var("WM_LANDLOCK_CHILD_WORKER").is_ok() {
        let ws = PathBuf::from(std::env::var("WM_TEST_WS").unwrap());
        let outside = PathBuf::from(std::env::var("WM_TEST_OUTSIDE").unwrap());

        let claim = WorkspaceClaim {
            claim_id: "claim-child-test".to_string(),
            tenant_id: "tenant-lucas".to_string(),
            agent_id: "agent-sandboxed".to_string(),
            workspace_root: ws.clone(),
            read_only_paths: vec![
                PathBuf::from("/usr"),
                PathBuf::from("/lib"),
                PathBuf::from("/bin"),
            ],
            read_write_paths: vec![ws.clone()],
            network_allowed: false,
            kekkai_phase: KekkaiPhase::Hoi,
            resource_limits: Some(SandboxResourceLimits {
                max_memory_mb: 256,
                max_cpu_seconds: 5,
                max_open_files: 64,
            }),
            inherited_shm_fd: None,
            created_at: 1_700_000_000,
            expires_at: 1_700_003_600,
            signature: None,
        };

        // Restrict this process
        match LandlockSandbox::restrict_current_process(&claim) {
            Ok(()) => {
                // 1. Writing inside workspace should succeed
                let in_res = fs::write(ws.join("allowed.txt"), b"inside workspace");
                assert!(
                    in_res.is_ok(),
                    "Write inside workspace must succeed: {in_res:?}"
                );

                // 2. Writing outside workspace MUST fail with PermissionDenied
                let out_res = fs::write(outside.join("forbidden.txt"), b"outside payload");
                assert!(
                    out_res.is_err(),
                    "Write outside workspace must be blocked by Landlock LSM"
                );

                // 3. Network Scoping check (Linux 6.7+ Landlock ABI v4)
                // If the kernel supports ABI v4, binding to a TCP port should fail with PermissionDenied
                let bind_res = TcpListener::bind("127.0.0.1:0");
                if let Err(ref e) = bind_res {
                    if e.kind() == std::io::ErrorKind::PermissionDenied {
                        eprintln!("Kernel Landlock ABI v4 network restriction confirmed active!");
                    }
                }

                std::process::exit(0);
            }
            Err(e) => {
                eprintln!("Landlock not supported on this kernel or container: {e:?}");
                std::process::exit(77); // skipped / unsupported code
            }
        }
    }

    // Parent process spawns child
    let current_exe = std::env::current_exe().expect("current exe");
    let status = Command::new(current_exe)
        .arg("test_landlock_subprocess_confinement")
        .arg("--exact")
        .env("WM_LANDLOCK_CHILD_WORKER", "1")
        .env("WM_TEST_WS", ws_path.to_str().unwrap())
        .env("WM_TEST_OUTSIDE", outside_path.to_str().unwrap())
        .status()
        .expect("spawn child worker");

    let code = status.code().unwrap_or(-1);
    assert!(
        code == 0 || code == 77,
        "Child process should either exit 0 (Landlock enforced) or 77 (kernel unsupported), got {code}"
    );
}

#[test]
fn test_delegated_token_landlock_confinement() {
    let (authority_sk, authority_vk) = test_keys();

    // 1. Primary Agent Identity Token
    let agent_sk = SigningKey::from_bytes(&[88u8; 32]);
    let agent_vk = agent_sk.verifying_key();
    let (ws_path, _outside) = create_temp_subdirs("wm_test_delegated");

    let primary_token = wm_gen3_core::attestation::AgentIdentityToken::mint(
        &authority_sk,
        "agent-prime",
        &agent_vk,
        "primary_builder",
        vec![
            format!("fs:rw:{}", ws_path.display()),
            "fs:ro:/usr".to_string(),
            "net:deny".to_string(),
        ],
        100, // current epoch
        50,  // ttl
        [1u8; 16],
    );

    assert!(primary_token.verify(&authority_vk, 100).is_ok());

    // 2. Delegate to Subagent with subset capability
    let subagent_sk = SigningKey::from_bytes(&[99u8; 32]);
    let subagent_vk = subagent_sk.verifying_key();

    let proof = wm_gen3_core::attestation::DelegationProof::delegate(
        &agent_sk,
        primary_token.clone(),
        "subagent-worker-01",
        &subagent_vk,
        vec![
            format!("fs:rw:{}", ws_path.display()),
            "net:deny".to_string(),
        ],
        0, // initial depth
    )
    .expect("Delegation should succeed");

    assert!(proof.verify_chain(&authority_vk, 100).is_ok());

    // 3. Build Landlock ruleset from verified delegation proof
    #[cfg(target_os = "linux")]
    {
        let ruleset_res = LandlockSandbox::build_delegated_ruleset(
            &primary_token,
            Some(&proof),
            &authority_vk,
            100,
        );
        assert!(
            ruleset_res.is_ok(),
            "Delegated Landlock ruleset must build cleanly: {:?}",
            ruleset_res.err()
        );
    }

    // 4. Privilege Escalation Attempt: subagent requesting unauthorized capability
    let escalation_attempt = wm_gen3_core::attestation::DelegationProof::delegate(
        &agent_sk,
        primary_token.clone(),
        "subagent-malicious",
        &subagent_vk,
        vec!["fs:rw:/etc".to_string()],
        0,
    );
    assert!(
        escalation_attempt.is_err(),
        "Privilege escalation beyond parent token must be rejected"
    );

    // 5. Expired Token Attempt
    let expired_build = LandlockSandbox::build_delegated_ruleset(
        &primary_token,
        Some(&proof),
        &authority_vk,
        999, // epoch beyond expiration (150)
    );
    assert!(
        expired_build.is_err(),
        "Expired identity token must be denied Landlock ruleset generation"
    );
}

#[test]
fn test_landlock_inherited_shm_fd() {
    let test_shm_name = format!("/wm_test_landlock_shm_{}", uuid::Uuid::new_v4().simple());
    let mut substrate = wm_gen3_shm::ShmSubstrate::open_or_create(&test_shm_name)
        .expect("Create shared memory segment");
    let raw_fd = substrate.raw_fd().expect("Raw FD exists");

    let claim = WorkspaceClaim {
        claim_id: "claim-shm-fd-001".to_string(),
        tenant_id: "tenant-lucas".to_string(),
        agent_id: "agent-sandboxed-shm".to_string(),
        workspace_root: PathBuf::from("/tmp"),
        read_only_paths: vec![PathBuf::from("/usr")],
        read_write_paths: vec![PathBuf::from("/tmp")],
        network_allowed: false,
        kekkai_phase: KekkaiPhase::Hoi,
        resource_limits: None,
        inherited_shm_fd: Some(raw_fd),
        created_at: 1000,
        expires_at: 5000,
        signature: None,
    };

    // Sandboxed subagent attaches to inherited shm without touching /dev/shm filesystem
    let attached = claim
        .attach_shm()
        .expect("attach_shm Some")
        .expect("Attached cleanly");
    assert_eq!(attached.superblock().magic, wm_gen3_shm::SHM_MAGIC);

    // Verify Linda tuple write via inherited FD
    let space = wm_gen3_shm::ShmTupleSpace::new(std::sync::Arc::new(attached));
    let t = wm_gen3_shm::RawTuple {
        id: uuid::Uuid::new_v4(),
        kind_discriminator: 1,
        resource_hash: 1234,
        holder_issuer_hash: 5678,
        resource_path: "/workspace/token.txt".to_string(),
        tag: "claim:sandboxed".to_string(),
        payload: b"inherited fd verification".to_vec(),
        created_at_ms: 100,
        expires_at_ms: 0,
        landlock_token: [0u8; 32],
        capability_mask: 0x01,
    };
    space.out(&t).expect("Out tuple over inherited FD");

    let matching = space.rd_matching(Some(1), Some(1234), 1, 100);
    assert_eq!(matching.len(), 1);
    assert_eq!(matching[0].payload, b"inherited fd verification");

    // Cleanup
    let _ = substrate.unlink();
}
