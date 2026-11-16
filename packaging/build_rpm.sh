#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  build_rpm.sh – Erzeugt .rpm-Pakete für axb35-suite (Fedora)
#  
#  Aufruf:   bash packaging/build_rpm.sh [all|standard|mok]
#  Output:   dist/axb35-suite-1.2-1.fc.noarch.rpm
#            dist/axb35-suite-mok-1.2-1.fc.noarch.rpm
# ═══════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"      # → axb35-suite/
DIST_DIR="${SCRIPT_DIR}/dist"
BUILD_TOP="/tmp/rpm-build-$$"

PKG_NAME="axb35-suite"
PKG_VERSION="1.2"
PKG_RELEASE="1"

# ─── Farben ──────────────────────────────────────────────
G='\033[0;32m'; Y='\033[1;33m'; B='\033[1;34m'; N='\033[0m'
info()  { echo -e "${B}[INFO]${N} $*"; }
ok()    { echo -e "${G}[OK]${N}   $*"; }
warn()  { echo -e "${Y}[WARN]${N} $*"; }

# ─── Cleanup ─────────────────────────────────────────────
cleanup() { rm -rf "$BUILD_TOP"; }
trap cleanup EXIT

# ─── Setup RPM build tree ────────────────────────────────
setup_build_tree() {
    mkdir -p "${BUILD_TOP}"/{SPECS,SOURCES,BUILD,RPMS,SRPMS}
    
    # Copy spec file
    cp "${SCRIPT_DIR}/axb35-suite.spec" "${BUILD_TOP}/SPECS/"
    
    # Create source tarball (what %setup unpacks)
    local src_dir="${BUILD_TOP}/src-stage/${PKG_NAME}-${PKG_VERSION}"
    mkdir -p "${src_dir}/src"
    
    cp "${REPO_ROOT}/Makefile"              "${src_dir}/"
    cp "${REPO_ROOT}/src/ec_su_axb35.c"     "${src_dir}/src/"
    cp "${SCRIPT_DIR}/dkms.conf"            "${src_dir}/"
    cp "${REPO_ROOT}/python-gui/axb35_monitor_gui.py" "${src_dir}/axb35_monitor_gui.py"
    
    # Create tarball (name must match Source0 in spec)
    tar -czf "${BUILD_TOP}/SOURCES/${PKG_NAME}-${PKG_VERSION}.tar.gz" \
        -C "${BUILD_TOP}/src-stage" "${PKG_NAME}-${PKG_VERSION}"
}

# ─── Build one variant ──────────────────────────────────
build_rpm() {
    local variant="$1"   # "standard" or "mok"
    
    info "Building RPM: ${variant}"
    
    local -a rpm_args=(
        --define "_topdir ${BUILD_TOP}"
        --define "dist .fc"
        --nodeps
    )
    
    if [ "$variant" = "mok" ]; then
        rpm_args+=(--define "mok 1")
    fi
    
    rpmbuild -bb \
        "${rpm_args[@]}" \
        "${BUILD_TOP}/SPECS/axb35-suite.spec" 2>&1 | sed 's/^/       /'
    
    # Find and copy the resulting .rpm
    local rpm_file=""
    if [ "$variant" = "mok" ]; then
        rpm_file=$(find "${BUILD_TOP}/RPMS" -name "*${PKG_NAME}-mok*.rpm" 2>/dev/null | head -1)
    else
        rpm_file=$(find "${BUILD_TOP}/RPMS" -name "${PKG_NAME}-${PKG_VERSION}*.rpm" ! -name "*mok*" 2>/dev/null | head -1)
    fi
    
    if [ -z "$rpm_file" ]; then
        # Fallback: any .rpm in RPMS/
        rpm_file=$(find "${BUILD_TOP}/RPMS" -name "*.rpm" 2>/dev/null | sort | tail -1)
    fi
    
    if [ -n "$rpm_file" ] && [ -f "$rpm_file" ]; then
        cp "$rpm_file" "${DIST_DIR}/"
        ok "Created: $(basename "$rpm_file") ($(du -h "$rpm_file" | cut -f1))"
    else
        warn "No .rpm found! Checking RPMS dir:"
        find "${BUILD_TOP}/RPMS" -type f 2>/dev/null || echo "(empty)"
        return 1
    fi
}

# ─── Main ────────────────────────────────────────────────
main() {
    local target="${1:-all}"
    
    # Check prerequisites
    if ! command -v rpmbuild &>/dev/null; then
        echo -e "${Y}[ERROR]${N} rpmbuild not found. Install with: sudo apt install rpm"
        exit 1
    fi
    
    info "RPM build environment:"
    info "  rpmbuild: $(rpmbuild --version 2>&1 | head -1)"
    echo ""
    
    setup_build_tree
    mkdir -p "$DIST_DIR"
    
    case "${target}" in
        standard) build_rpm "standard" ;;
        mok)      build_rpm "mok" ;;
        all)
            build_rpm "standard"
            echo ""
            # Reset RPMS for MOK build
            rm -f "${BUILD_TOP}/RPMS/"*/*.rpm 2>/dev/null || true
            setup_build_tree
            build_rpm "mok"
            ;;
        *)
            echo "Usage: $0 [all|standard|mok]"
            exit 1
            ;;
    esac
    
    echo ""
    ok "All done! RPM packages in: ${DIST_DIR}/"
    echo ""
    ls -lh "${DIST_DIR}"/*.rpm 2>/dev/null || true
    echo ""
    echo "  Install (Fedora / dnf):"
    echo "    sudo dnf install ./${PKG_NAME}-${PKG_VERSION}-1.fc.noarch.rpm"
    echo ""
    echo "  Or manually:"
    echo "    sudo rpm -i ${DIST_DIR}/${PKG_NAME}-${PKG_VERSION}-1.fc.noarch.rpm"
}

main "$@"
