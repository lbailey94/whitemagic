const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const lib_mod = b.createModule(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
        .link_libc = true,
    });

    // Static library (whitemagic-zig)
    const lib = b.addLibrary(.{
        .linkage = .static,
        .name = "whitemagic-zig",
        .root_module = lib_mod,
    });
    b.installArtifact(lib);

    // Shared library (whitemagic)
    const lib_shared = b.addLibrary(.{
        .linkage = .dynamic,
        .name = "whitemagic",
        .root_module = lib_mod,
    });
    b.installArtifact(lib_shared);
}
