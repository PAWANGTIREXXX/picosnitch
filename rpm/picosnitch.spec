Name:           picosnitch
Version:        0.12.0
Release:        1%{?dist}
License:        GPL-3.0
Summary:        Monitor network traffic per executable using BPF
Url:            https://github.com/elesiuta/picosnitch
Source:         https://github.com/elesiuta/picosnitch/releases/download/v%{version}/picosnitch.tar.gz
BuildRequires:  python3
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-psutil
Requires:       python3
Requires:       bcc
Requires:       python3-psutil
Requires:       python3-requests
Suggests:       python3-pandas
Suggests:       python3-plotly

%if 0%{?fedora}%{?suse_version}%{?mageia}
BuildRequires:  python3-wheel
Requires:       python3-dbus
%endif

%if 0%{?suse_version}
BuildRequires:  python3-curses
Requires:       python3-curses
%endif

%if 0%{?fedora}
BuildRequires:  systemd-rpm-macros
BuildRequires:  systemd-units
BuildRequires:  util-linux-core
%endif

%description 
Monitors your bandwidth, breaking down traffic by executable, hash, parent, domain, port, or user over time

%global debug_package %{nil}

%prep 
%setup -c -q -n %{name}

%build
%py3_build

%install
%py3_install
mkdir -vp %{buildroot}%{_unitdir}
install -D -m 644 debian/picosnitch.service %{buildroot}%{_unitdir}/%{name}.service

%post
%systemd_post %{name}.service
 
%preun
%systemd_preun %{name}.service
 
%postun
%systemd_postun_with_restart %{name}.service

%files -n picosnitch
%license LICENSE
%doc README.md
%{python3_sitelib}/picosnitch-*.egg-info/
%{python3_sitelib}/picosnitch.py
/usr/bin/picosnitch
%{_unitdir}/%{name}.service
%if 0%{?fedora}%{?suse_version}%{?mageia}
%{python3_sitelib}/__pycache__/picosnitch.cpython-*.pyc
%endif

%changelog
* Sun Feb 19 2023 Eric Lesiuta <elesiuta@gmail.com> - 0.12.0-1
- see releases on github for changes

