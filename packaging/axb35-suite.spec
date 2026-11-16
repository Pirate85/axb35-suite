%global ekg_version 1.1
%global debug_package %{nil}
Name:           axb35-suite
Version:        1.2
Release:        1%{?dist}
Summary:        Fan control driver + system monitor for Sixunited AXB35-02 EC

License:        GPL-3.0-or-later
URL:            https://github.com/Pirate85/axb35-suite
Source0:        %{name}-%{version}.tar.gz

Requires:       dkms
Requires:       kernel-devel
Requires:       python3-tkinter
Requires:       smartmontools
Requires(pre):  systemd
Recommends:     openssl

%description
Kernel module and all-in-one GUI for fan control on AMD Strix Halo
mini PCs with the Sixunited AXB35-02 embedded controller board.

Compatible hardware: GMKtec EVO-X2, Bosgame M5, FEVM FA-EX9,
Peladn YO1, NIMO AI MiniPC, Corsair AI Workstation 300.

Features: DKMS kernel module (auto-rebuild on kernel updates),
live system monitor (CPU/GPU/NVMe/RAM/VRAM/fans with clock rates),
fan curve configuration GUI with persistence via systemd service.

# ─── MOK Subpackage ────────────────────────────────────────
%package -n axb35-suite-mok
Summary:        AXB35 Suite – Secure Boot (MOK) variant for Fedora
Requires:       dkms
Requires:       kernel-devel
Requires:       python3-tkinter
Requires:       smartmontools
Requires(pre):  systemd
Recommends:     openssl

%description -n axb35-suite-mok
Secure Boot (MOK) version of axb35-suite. Automatically signs the
kernel module and enrolls the MOK key at first boot. Use this variant
if Secure Boot is enabled in your UEFI/BIOS settings.

# ─── Build & Install ──────────────────────────────────────
%prep
%setup -q

%build
# Nothing to compile – DKMS handles kernel module build at install time.

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/src/ec_su_axb35-%{ekg_version}/src
mkdir -p %{buildroot}/usr/local/bin
mkdir -p %{buildroot}/usr/share/applications

# DKMS source
cp Makefile              %{buildroot}/usr/src/ec_su_axb35-%{ekg_version}/
cp src/ec_su_axb35.c     %{buildroot}/usr/src/ec_su_axb35-%{ekg_version}/src/
cp dkms.conf             %{buildroot}/usr/src/ec_su_axb35-%{ekg_version}/

# GUI binary
install -m 0755 axb35_monitor_gui.py %{buildroot}/usr/local/bin/axb35-system-monitor

# Desktop entry
cat > %{buildroot}/usr/share/applications/axb35-suite.desktop << 'DESK'
[Desktop Entry]
Type=Application
Name=Axb35-monitor
Comment=Fan control & system monitor for Sixunited AXB35-02
Exec=/usr/local/bin/axb35-system-monitor
Icon=utilities-system-monitor
Terminal=false
Categories=System;Monitor;
StartupWMClass=Axb35-monitor
DESK

# ─── Files ────────────────────────────────────────────────
%files
%defattr(-,root,root,-)
/usr/src/ec_su_axb35-%{ekg_version}/Makefile
/usr/src/ec_su_axb35-%{ekg_version}/dkms.conf
/usr/src/ec_su_axb35-%{ekg_version}/src/
/usr/local/bin/axb35-system-monitor
/usr/share/applications/axb35-suite.desktop

%files -n axb35-suite-mok
%defattr(-,root,root,-)
/usr/src/ec_su_axb35-%{ekg_version}/Makefile
/usr/src/ec_su_axb35-%{ekg_version}/dkms.conf
/usr/src/ec_su_axb35-%{ekg_version}/src/
/usr/local/bin/axb35-system-monitor
/usr/share/applications/axb35-suite.desktop

# ─── Scriptlets: Standard ─────────────────────────────────
%post
echo "[axb35-suite] Setting up DKMS module..."
dkms add -m ec_su_axb35 -v %{ekg_version} 2>/dev/null || true
dkms build -m ec_su_axb35 -v %{ekg_version} 2>/dev/null || true
dkms install -m ec_su_axb35 -v %{ekg_version} 2>/dev/null || true

echo "ec_su_axb35" > /etc/modules-load.d/ec_su_axb35.conf
modprobe ec_su_axb35 2>/dev/null || true

if [ -f /etc/systemd/system/fancontrol.service ]; then
    systemctl enable fancontrol 2>/dev/null || true
fi
systemctl daemon-reload 2>/dev/null || true

echo "[axb35-suite] Install complete. Launch 'Axb35-monitor' from your app menu."

%preun
if lsmod | grep -q ec_su_axb35; then
    echo "[axb35-suite] Unloading kernel module..."
    rmmod ec_su_axb35 2>/dev/null || true
fi

%postun
if [ $1 -eq 0 ]; then
    echo "[axb35-suite] Removing DKMS module + configs..."
    dkms remove -m ec_su_axb35 -v %{ekg_version} --all 2>/dev/null || true
    rm -f /etc/modules-load.d/ec_su_axb35.conf
    if [ -f /etc/systemd/system/fancontrol.service ]; then
        systemctl disable fancontrol 2>/dev/null || true
        rm -f /etc/systemd/system/fancontrol.service
    fi
    systemctl daemon-reload 2>/dev/null || true
fi

# ─── Scriptlets: MOK variant ──────────────────────────────
%post -n axb35-suite-mok
echo "[axb35-suite-mok] Setting up DKMS module + signing..."
dkms add -m ec_su_axb35 -v %{ekg_version} 2>/dev/null || true

# Generate MOK key if not present
MOK_KEY_DIR=/var/lib/shim-sources/mok
if [ ! -f "${MOK_KEY_DIR}/mok.key" ]; then
    mkdir -p "${MOK_KEY_DIR}"
    openssl req -config /dev/null -new -x509 -newkey rsa:2048 \
        -out "${MOK_KEY_DIR}/mok.crt" -keyout "${MOK_KEY_DIR}/mok.key" \
        -days 36500 -nodes -subj "/CN=AXB35 Suite MOK/" 2>/dev/null || true
fi

dkms build -m ec_su_axb35 -v %{ekg_version} 2>/dev/null || true
dkms install -m ec_su_axb35 -v %{ekg_version} 2>/dev/null || true

echo "ec_su_axb35" > /etc/modules-load.d/ec_su_axb35.conf
modprobe ec_su_axb35 2>/dev/null || true

if [ -f /etc/systemd/system/fancontrol.service ]; then
    systemctl enable fancontrol 2>/dev/null || true
fi
systemctl daemon-reload 2>/dev/null || true

echo ""
echo "[axb35-suite-mok] ⚠️  Secure Boot: Reboot required to enroll MOK key."
echo "                  At the blue MOK screen, select 'Enroll MOK'."
echo ""
echo "[axb35-suite-mok] Install complete. Launch 'Axb35-monitor' from your app menu."

%preun -n axb35-suite-mok
if lsmod | grep -q ec_su_axb35; then
    rmmod ec_su_axb35 2>/dev/null || true
fi

%postun -n axb35-suite-mok
if [ $1 -eq 0 ]; then
    dkms remove -m ec_su_axb35 -v %{ekg_version} --all 2>/dev/null || true
    rm -f /etc/modules-load.d/ec_su_axb35.conf
    if [ -f /etc/systemd/system/fancontrol.service ]; then
        systemctl disable fancontrol 2>/dev/null || true
        rm -f /etc/systemd/system/fancontrol.service
    fi
    systemctl daemon-reload 2>/dev/null || true
fi

%changelog
* Thu Nov 16 2026 Pirate85 <Pirate85@web.de> - 1.2-1
- Initial RPM packaging (Fedora support)
- GUI: CPU/GPU clock rate display in usage bars
* Tue Oct 28 2026 Pirate85 <Pirate85@web.de> - 1.1-1
- v1.1 initial release (DEB)
