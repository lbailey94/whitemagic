//! Network posture by observation (board item 2, `wm doctor --network`).
//!
//! "Local-only" is an asserted, tested property, not a config-file
//! assumption: the audit reads the live socket tables (`/proc/net/tcp*`),
//! attributes sockets to WhiteMagic processes and the fleet transport
//! (syncthing), and flags any established connection to a non-LAN address.
//! Feeds off the egress lesson (board item 8): stock defaults announced the
//! fleet to global discovery + relays — verified closure is re-verified here
//! on every doctor run.
//!
//! Pure functions (`classify_addr`, `parse_proc_net`, attribution) are
//! separated from the `/proc` walkers so tests inject synthetic table text.

use std::collections::BTreeMap;
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};

/// Where an address sits on the LAN/local-only map.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AddrClass {
    Loopback,
    LinkLocal,
    Lan,
    Unspecified,
    Global,
}

/// Classify an address against the local-only doctrine.
///
/// Loopback, link-local and RFC1918/ULA LAN addresses are inside the fence;
/// everything routable beyond it is Global. IPv4-mapped IPv6 is unwrapped to
/// its v4 class.
#[must_use]
pub fn classify_addr(addr: &IpAddr) -> AddrClass {
    let v4 = match addr {
        IpAddr::V4(v4) => Some(*v4),
        IpAddr::V6(v6) => v6.to_ipv4_mapped(),
    };
    if let Some(v4) = v4 {
        return classify_v4(v4);
    }
    let v6 = match addr {
        IpAddr::V6(v6) => *v6,
        IpAddr::V4(_) => unreachable!("v4 handled above"),
    };
    if v6.is_loopback() {
        AddrClass::Loopback
    } else if v6.is_unspecified() {
        AddrClass::Unspecified
    } else if (v6.segments()[0] & 0xffc0) == 0xfe80 {
        AddrClass::LinkLocal
    } else if (v6.segments()[0] & 0xfe00) == 0xfc00 {
        AddrClass::Lan // ULA fc00::/7 — the IPv6 LAN fence
    } else {
        AddrClass::Global
    }
}

const fn classify_v4(v4: Ipv4Addr) -> AddrClass {
    let o = v4.octets();
    if v4.is_loopback() {
        AddrClass::Loopback
    } else if v4.is_unspecified() {
        AddrClass::Unspecified
    } else if o[0] == 169 && o[1] == 254 {
        AddrClass::LinkLocal
    } else if o[0] == 10 || (o[0] == 172 && (o[1] & 0xf0) == 16) || (o[0] == 192 && o[1] == 168) {
        AddrClass::Lan
    } else {
        AddrClass::Global
    }
}

/// One endpoint from a `/proc/net` row.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Endpoint {
    pub addr: IpAddr,
    pub port: u16,
}

/// One socket row from `/proc/net/tcp` or `/proc/net/tcp6`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SocketRow {
    pub local: Endpoint,
    pub remote: Endpoint,
    /// TCP state hex (`01` = ESTABLISHED, `0A` = LISTEN).
    pub state: String,
    pub inode: u64,
}

impl SocketRow {
    #[must_use]
    pub fn is_established(&self) -> bool {
        self.state == "01"
    }

    #[must_use]
    pub fn is_listening(&self) -> bool {
        self.state == "0A"
    }
}

/// Parse the text of a `/proc/net/tcp` or `/proc/net/tcp6` table.
///
/// Both share the layout; addresses differ only in width (8 vs 32 hex
/// chars). Words are printed little-endian per u32 on the platforms this
/// runs on, so each 4-byte word is byte-reversed — the same rule makes
/// `0100007F` read as 127.0.0.1 (v4) and `...01000000` read as ::1 (v6).
#[must_use]
pub fn parse_proc_net(text: &str) -> Vec<SocketRow> {
    let mut rows = Vec::new();
    for line in text.lines().skip(1) {
        let fields: Vec<&str> = line.split_whitespace().collect();
        if fields.len() < 10 {
            continue;
        }
        let (Some(local), Some(remote), state, Some(inode)) = (
            parse_endpoint(fields[1]),
            parse_endpoint(fields[2]),
            fields[3].to_string(),
            fields[9].parse::<u64>().ok(),
        ) else {
            continue;
        };
        rows.push(SocketRow {
            local,
            remote,
            state,
            inode,
        });
    }
    rows
}

fn parse_endpoint(field: &str) -> Option<Endpoint> {
    let (addr_hex, port_hex) = field.split_once(':')?;
    if addr_hex.len() != 8 && addr_hex.len() != 32 {
        return None;
    }
    let port = u16::from_str_radix(port_hex, 16).ok()?;
    let bytes = word_reversed_bytes(addr_hex)?;
    let addr = if addr_hex.len() == 8 {
        IpAddr::V4(Ipv4Addr::new(bytes[0], bytes[1], bytes[2], bytes[3]))
    } else {
        let mut octets = [0u8; 16];
        octets.copy_from_slice(&bytes);
        IpAddr::V6(Ipv6Addr::from(octets))
    };
    Some(Endpoint { addr, port })
}

/// Hex-decode an 8- or 32-char address field, reversing each 4-byte word.
fn word_reversed_bytes(hex: &str) -> Option<Vec<u8>> {
    if hex.len() % 8 != 0 {
        return None;
    }
    let mut out = Vec::with_capacity(hex.len() / 2);
    for word in hex.as_bytes().chunks(8) {
        let mut word_bytes = [0u8; 4];
        for (i, pair) in word.chunks(2).enumerate() {
            word_bytes[i] = u8::from_str_radix(std::str::from_utf8(pair).ok()?, 16).ok()?;
        }
        out.extend(word_bytes.iter().rev());
    }
    Some(out)
}

/// A process observed holding sockets, with its posture-relevant sockets.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SubjectSockets {
    pub pid: u32,
    pub comm: String,
    pub established_remote: Vec<Endpoint>,
    /// Listening sockets not bound to loopback (LAN inbound exposure,
    /// disclosed — the fleet rides LAN; egress is what counts as an issue).
    pub lan_listeners: Vec<Endpoint>,
}

impl SubjectSockets {
    #[must_use]
    pub fn is_fleet_transport(&self) -> bool {
        self.comm == "syncthing"
    }
}

/// An established connection from a subject process to a non-LAN address.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EgressViolation {
    pub pid: u32,
    pub comm: String,
    pub remote: Endpoint,
}

/// Result of a live audit run.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct NetworkPosture {
    pub platform_supported: bool,
    pub subjects: Vec<SubjectSockets>,
    pub violations: Vec<EgressViolation>,
}

/// Is this process one of the audit's subjects? WhiteMagic binaries
/// (`wm`, `wm-mcp`, `wm-gateway`, ...) plus the fleet transport.
#[must_use]
pub fn is_subject_comm(comm: &str) -> bool {
    comm == "syncthing" || comm == "wm" || comm.starts_with("wm-")
}

/// Attribute parsed socket rows to subject processes.
/// `pid_comms`: `(pid, comm)` for every candidate process;
/// `pid_inodes`: `(pid, socket inode)` pairs harvested from `/proc/<pid>/fd`.
#[must_use]
pub fn attribute_sockets(
    rows: &[SocketRow],
    pid_comms: &[(u32, String)],
    pid_inodes: &[(u32, u64)],
) -> Vec<SubjectSockets> {
    let mut by_inode: BTreeMap<u64, u32> = BTreeMap::new();
    for (pid, inode) in pid_inodes {
        by_inode.insert(*inode, *pid);
    }
    let mut subjects: BTreeMap<u32, SubjectSockets> = BTreeMap::new();
    for (pid, comm) in pid_comms {
        if is_subject_comm(comm) {
            subjects.insert(
                *pid,
                SubjectSockets {
                    pid: *pid,
                    comm: comm.clone(),
                    established_remote: Vec::new(),
                    lan_listeners: Vec::new(),
                },
            );
        }
    }
    for row in rows {
        let Some(pid) = by_inode.get(&row.inode) else {
            continue;
        };
        let Some(subject) = subjects.get_mut(pid) else {
            continue;
        };
        if row.is_established() {
            subject.established_remote.push(row.remote.clone());
        } else if row.is_listening() {
            let class = classify_addr(&row.local.addr);
            if !matches!(class, AddrClass::Loopback) {
                subject.lan_listeners.push(row.local.clone());
            }
        }
    }
    subjects.into_values().collect()
}

/// Grade attributed sockets: any established connection to a Global address
/// is an egress violation (the relay-socket lesson, asserted by observation).
#[must_use]
pub fn grade(subjects: &[SubjectSockets]) -> Vec<EgressViolation> {
    let mut violations = Vec::new();
    for subject in subjects {
        for remote in &subject.established_remote {
            if classify_addr(&remote.addr) == AddrClass::Global {
                violations.push(EgressViolation {
                    pid: subject.pid,
                    comm: subject.comm.clone(),
                    remote: remote.clone(),
                });
            }
        }
    }
    violations
}

/// Harvest `(pid, socket-inode)` pairs for every process whose comm matches
/// a subject, by scanning `/proc/<pid>/fd/*` for `socket:[inode]` links.
fn harvest_socket_inodes(pids: &[(u32, String)]) -> std::io::Result<Vec<(u32, u64)>> {
    let mut found = Vec::new();
    for (pid, _) in pids {
        let fd_dir = format!("/proc/{pid}/fd");
        let entries = match std::fs::read_dir(&fd_dir) {
            Ok(e) => e,
            Err(_) => continue, // vanished or unreadable — skip honestly
        };
        for entry in entries.flatten() {
            let Ok(target) = std::fs::read_link(entry.path()) else {
                continue;
            };
            let target = target.to_string_lossy();
            let Some(rest) = target.strip_prefix("socket:[") else {
                continue;
            };
            let Some(inode) = rest.strip_suffix(']').and_then(|s| s.parse::<u64>().ok()) else {
                continue;
            };
            found.push((*pid, inode));
        }
    }
    Ok(found)
}

/// List candidate `(pid, comm)` pairs from `/proc`.
fn scan_comms() -> std::io::Result<Vec<(u32, String)>> {
    let mut pairs = Vec::new();
    for entry in std::fs::read_dir("/proc")?.flatten() {
        let Ok(name) = entry.file_name().into_string() else {
            continue;
        };
        let Ok(pid) = name.parse::<u32>() else {
            continue;
        };
        let Ok(comm) = std::fs::read_to_string(format!("/proc/{pid}/comm")) else {
            continue;
        };
        pairs.push((pid, comm.trim().to_string()));
    }
    Ok(pairs)
}

/// Run the live audit.
///
/// Returns a posture with `platform_supported == false` when the socket
/// tables are unavailable (non-Linux or hardened mounts) — the caller
/// discloses that honestly instead of asserting health.
#[must_use]
pub fn audit() -> NetworkPosture {
    let Some(tcp) = std::fs::read_to_string("/proc/net/tcp").ok() else {
        return NetworkPosture::default();
    };
    let tcp6 = std::fs::read_to_string("/proc/net/tcp6").unwrap_or_default();
    let mut rows = parse_proc_net(&tcp);
    rows.extend(parse_proc_net(&tcp6));

    let comms = match scan_comms() {
        Ok(c) => c,
        Err(_) => return NetworkPosture::default(),
    };
    let inodes = harvest_socket_inodes(&comms).unwrap_or_default();
    let subjects = attribute_sockets(&rows, &comms, &inodes);
    let violations = grade(&subjects);
    NetworkPosture {
        platform_supported: true,
        subjects,
        violations,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::{IpAddr, Ipv4Addr};

    fn v4(o: [u8; 4]) -> IpAddr {
        IpAddr::V4(Ipv4Addr::from(o))
    }

    #[test]
    fn classifies_the_local_only_fence() {
        assert_eq!(classify_addr(&v4([127, 0, 0, 1])), AddrClass::Loopback);
        assert_eq!(classify_addr(&v4([10, 0, 0, 57])), AddrClass::Lan);
        assert_eq!(classify_addr(&v4([172, 16, 5, 4])), AddrClass::Lan);
        assert_eq!(classify_addr(&v4([192, 168, 1, 2])), AddrClass::Lan);
        assert_eq!(classify_addr(&v4([169, 254, 3, 3])), AddrClass::LinkLocal);
        assert_eq!(classify_addr(&v4([0, 0, 0, 0])), AddrClass::Unspecified);
        assert_eq!(classify_addr(&v4([8, 8, 8, 8])), AddrClass::Global);
        // The relay address from the egress lesson stays Global.
        assert_eq!(classify_addr(&v4([209, 195, 13, 146])), AddrClass::Global);
    }

    #[test]
    fn classifies_v6_including_v4_mapped() {
        assert_eq!(
            classify_addr(&IpAddr::V6("::1".parse().unwrap())),
            AddrClass::Loopback
        );
        assert_eq!(
            classify_addr(&IpAddr::V6("fe80::1".parse().unwrap())),
            AddrClass::LinkLocal
        );
        assert_eq!(
            classify_addr(&IpAddr::V6("fd00::5".parse().unwrap())),
            AddrClass::Lan
        );
        assert_eq!(
            classify_addr(&IpAddr::V6("2606:4700::1111".parse().unwrap())),
            AddrClass::Global
        );
        assert_eq!(
            classify_addr(&IpAddr::V6("::ffff:10.0.0.57".parse().unwrap())),
            AddrClass::Lan
        );
        assert_eq!(
            classify_addr(&IpAddr::V6("::ffff:209.195.13.146".parse().unwrap())),
            AddrClass::Global
        );
    }

    #[test]
    fn parses_proc_net_tcp_v4_rows() {
        // Header + one established row (LAN peer) + one listener. Addresses
        // are u32-LE: 10.0.0.57 prints as 3900000A (the reversed-addr quirk).
        let text = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n\
                    0: 3900000A:153A 3A00000A:8AB6 01 00000000:00000000 00:00000000 00000000  1000        0 12345 1\n\
                    1: 00000000:20BC 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 12346 1\n";
        let rows = parse_proc_net(text);
        assert_eq!(rows.len(), 2);

        let established = &rows[0];
        assert!(established.is_established());
        assert_eq!(
            established.local,
            Endpoint {
                addr: v4([10, 0, 0, 57]),
                port: 0x153A
            }
        );
        assert_eq!(
            established.remote,
            Endpoint {
                addr: v4([10, 0, 0, 58]),
                port: 0x8AB6
            }
        );
        assert_eq!(established.inode, 12345);

        let listener = &rows[1];
        assert!(listener.is_listening());
        assert_eq!(
            listener.local,
            Endpoint {
                addr: v4([0, 0, 0, 0]),
                port: 0x20BC
            }
        );
    }

    #[test]
    fn parses_proc_net_tcp6_v4_mapped_rows() {
        // ::ffff:10.0.0.57:8384 bound locally, established to ::ffff:10.0.0.58.
        // Each u32 word is byte-reversed on little-endian /proc output; the
        // FFFF0000 word decodes to the ff:ff bytes of the mapped prefix.
        let text = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n\
                    0: 0000000000000000FFFF00003900000A:20BC 0000000000000000FFFF00003A00000A:8AB6 01 00000000:00000000 00:00000000 00000000  1000        0 99999 1\n";
        let rows = parse_proc_net(text);
        assert_eq!(rows.len(), 1);
        let row = &rows[0];
        assert_eq!(
            row.local.addr,
            IpAddr::V6("::ffff:10.0.0.57".parse().unwrap())
        );
        assert_eq!(
            row.remote.addr,
            IpAddr::V6("::ffff:10.0.0.58".parse().unwrap())
        );
        assert_eq!(row.local.port, 0x20BC);
    }

    #[test]
    fn garbage_rows_are_skipped_not_fatal() {
        let text = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n\
                    0: not-an-address 00000000:0000 01 0 0 0 0 0 0\n\
                    1: 0A000039:153A 0A00003A:8AB6 01 00000000:00000000 00:00000000 00000000  1000        0 12345 1\n";
        let rows = parse_proc_net(text);
        assert_eq!(rows.len(), 1);
    }

    #[test]
    fn subject_match_covers_wm_binaries_and_fleet_transport_only() {
        assert!(is_subject_comm("wm"));
        assert!(is_subject_comm("wm-gateway"));
        assert!(is_subject_comm("wm-mcp"));
        assert!(is_subject_comm("syncthing"));
        assert!(!is_subject_comm("firefox"));
        assert!(!is_subject_comm("wmasterd"));
    }

    #[test]
    fn attribution_maps_inodes_to_subject_sockets() {
        let rows = vec![
            SocketRow {
                local: Endpoint {
                    addr: v4([10, 0, 0, 57]),
                    port: 40000,
                },
                remote: Endpoint {
                    addr: v4([209, 195, 13, 146]),
                    port: 22067,
                },
                state: "01".into(),
                inode: 100,
            },
            SocketRow {
                local: Endpoint {
                    addr: v4([10, 0, 0, 57]),
                    port: 40001,
                },
                remote: Endpoint {
                    addr: v4([10, 0, 0, 58]),
                    port: 22000,
                },
                state: "01".into(),
                inode: 101,
            },
            SocketRow {
                local: Endpoint {
                    addr: v4([0, 0, 0, 0]),
                    port: 21027,
                },
                remote: Endpoint {
                    addr: v4([0, 0, 0, 0]),
                    port: 0,
                },
                state: "0A".into(),
                inode: 102,
            },
            SocketRow {
                local: Endpoint {
                    addr: v4([127, 0, 0, 1]),
                    port: 8384,
                },
                remote: Endpoint {
                    addr: v4([0, 0, 0, 0]),
                    port: 0,
                },
                state: "0A".into(),
                inode: 103,
            },
        ];
        let comms = vec![
            (11u32, "wm".to_string()),
            (12u32, "syncthing".to_string()),
            (13u32, "firefox".to_string()),
        ];
        let inodes = vec![
            (11u32, 100u64),
            (12u32, 101u64),
            (12u32, 102u64),
            (12u32, 103u64),
            (13u32, 104u64),
        ];
        let subjects = attribute_sockets(&rows, &comms, &inodes);
        assert_eq!(subjects.len(), 2);

        let wm = subjects.iter().find(|s| s.comm == "wm").unwrap();
        assert_eq!(
            wm.established_remote,
            vec![Endpoint {
                addr: v4([209, 195, 13, 146]),
                port: 22067
            }]
        );
        let violations = grade(&subjects);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].comm, "wm");
        assert_eq!(violations[0].remote.addr, v4([209, 195, 13, 146]));

        let sync = subjects.iter().find(|s| s.comm == "syncthing").unwrap();
        assert!(sync.is_fleet_transport());
        // LAN-established + loopback listener → no violation from syncthing.
        assert!(violations.iter().all(|v| v.comm != "syncthing"));
        // The wildcard discovery listener is disclosed, not graded an issue.
        assert_eq!(
            sync.lan_listeners,
            vec![Endpoint {
                addr: v4([0, 0, 0, 0]),
                port: 21027
            }]
        );
        // firefox's socket (inode 104) matches no row and is not a subject.
    }

    #[test]
    fn lan_only_posture_grades_clean() {
        let rows = vec![SocketRow {
            local: Endpoint {
                addr: v4([10, 0, 0, 57]),
                port: 40000,
            },
            remote: Endpoint {
                addr: v4([10, 0, 0, 58]),
                port: 22000,
            },
            state: "01".into(),
            inode: 7,
        }];
        let comms = vec![(5u32, "wm-gateway".to_string())];
        let inodes = vec![(5u32, 7u64)];
        let subjects = attribute_sockets(&rows, &comms, &inodes);
        assert!(grade(&subjects).is_empty());
    }
}
