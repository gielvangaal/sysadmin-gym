Name:           gym-workload
Version:        %{gym_version}
Release:        1
Summary:        Sysadmin Gym practice payload
License:        MIT
BuildArch:      noarch
Prefix:         /opt/gym-workload

%description
An original data-only RPM for practicing local package transactions.

%install
install -d %{buildroot}/opt/gym-workload
printf 'gym payload %{version}\n' > %{buildroot}/opt/gym-workload/marker.txt

%files
%dir /opt/gym-workload
/opt/gym-workload/marker.txt
