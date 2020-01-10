%global commit                  fb4b94f493d4676014780a17d7c92de1c566a22d
%global gittag                  6.1.0.181
%global shortcommit             %(c=%{commit}; echo ${c:0:7})

%define spec_release            17

%define kmod_name		kvdo
%define kmod_driver_version	%{gittag}
%define kmod_rpm_release	%{spec_release}
%define kmod_kernel_version	3.10.0-693.el7
%define kmod_headers_version	%(rpm -qa kernel-devel | sed 's/^kernel-devel-//')
%define kmod_kbuild_dir		.
%define kmod_dependencies       %{nil}
%define kmod_build_dependencies	%{nil}
%define kmod_devel_package	0

%{!?dist: %define dist .el7_4}

Source0:        https://github.com/dm-vdo/%{kmod_name}/archive/%{commit}/%{kmod_name}-%{shortcommit}.tar.gz
%{nil}

%define findpat %( echo "%""P" )
%define __find_requires /usr/lib/rpm/redhat/find-requires.ksyms
%define __find_provides /usr/lib/rpm/redhat/find-provides.ksyms %{kmod_name} %{?epoch:%{epoch}:}%{version}-%{release}
%define sbindir %( if [ -d "/sbin" -a \! -h "/sbin" ]; then echo "/sbin"; else echo %{_sbindir}; fi )

Name:		kmod-kvdo
Version:	%{kmod_driver_version}
Release:	%{kmod_rpm_release}%{?dist}
Summary:	Kernel Modules for Virtual Data Optimizer
License:	GPLv2+
URL:		http://github.com/dm-vdo/kvdo
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires:	kernel-devel >= %{kmod_kernel_version}
BuildRequires:  redhat-rpm-config
BuildRequires:  kernel-debug >= %{kmod_kernel_version}
BuildRequires:	glibc
BuildRequires:	kernel-abi-whitelists
BuildRequires:  libuuid-devel
ExclusiveArch:	x86_64
ExcludeArch:    s390
ExcludeArch:    s390x
ExcludeArch:    ppc
ExcludeArch:    ppc64
ExcludeArch:    ppc64le
ExcludeArch:    aarch64
ExcludeArch:    i686
%global kernel_source() /usr/src/kernels/%{kmod_headers_version}

%global _use_internal_dependency_generator 0
Provides:	kernel-modules = %{kmod_kernel_version}.%{_target_cpu}
Provides:	kmod-%{kmod_name} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires(post):	%{sbindir}/weak-modules
Requires(postun):	%{sbindir}/weak-modules
Requires:	kernel >= %{kmod_kernel_version}
%if 0
Requires: firmware(%{kmod_name}) = ENTER_FIRMWARE_VERSION
%endif
%if "%{kmod_build_dependencies}" != ""
BuildRequires:  %{kmod_build_dependencies}
%endif
%if "%{kmod_dependencies}" != ""
Requires:       %{kmod_dependencies}
%endif
# if there are multiple kmods for the same driver from different vendors,
# they should conflict with each other.
Conflicts:	kmod-%{kmod_name}

%description
Virtual Data Optimizer (VDO) is a device mapper target that delivers
block-level deduplication, compression, and thin provisioning.

This package provides the kernel modules for VDO.

%if 0

%package -n kmod-kvdo-firmware
Version:	ENTER_FIRMWARE_VERSION
Summary:	Kernel Modules for Virtual Data Optimizer
Provides:	firmware(%{kmod_name}) = ENTER_FIRMWARE_VERSION
Provides:	kernel-modules = %{kmod_kernel_version}.%{_target_cpu}
%description -n  kmod-kvdo-firmware
Virtual Data Optimizer (VDO) is a device mapper target that delivers
block-level deduplication, compression, and thin provisioning.

This package provides the firmware for VDO.

%files -n kmod-kvdo-firmware
%defattr(644,root,root,755)
%{FIRMWARE_FILES}

%endif

# Development package
%if 0%{kmod_devel_package}
%package -n kmod-kvdo-devel
Version:	%{kmod_driver_version}
Requires:	kernel >= %{kmod_kernel_version}
Summary:	Kernel Modules for Virtual Data Optimizer

%description -n  kmod-kvdo-devel
Virtual Data Optimizer (VDO) is a device mapper target that delivers
block-level deduplication, compression, and thin provisioning.

This package provides the development files for VDO.

%files -n kmod-kvdo-devel
%defattr(644,root,root,755)
/usr/share/kmod-%{kmod_name}/Module.symvers
%endif

%post
modules=( $(find /lib/modules/%{kmod_headers_version}/extra/kmod-%{kmod_name} | grep '\.ko$') )
printf '%s\n' "${modules[@]}" >> /var/lib/rpm-kmod-posttrans-weak-modules-add

%pretrans -p <lua>
posix.unlink("/var/lib/rpm-kmod-posttrans-weak-modules-add")

%posttrans
if [ -f "/var/lib/rpm-kmod-posttrans-weak-modules-add" ]; then
	modules=( $(cat /var/lib/rpm-kmod-posttrans-weak-modules-add) )
	rm -rf /var/lib/rpm-kmod-posttrans-weak-modules-add
	printf '%s\n' "${modules[@]}" | %{sbindir}/weak-modules --add-modules
fi

%preun
rpm -ql kmod-kvdo-%{kmod_driver_version}-%{kmod_rpm_release}%{?dist}.$(arch) | grep '\.ko$' > /var/run/rpm-kmod-%{kmod_name}-modules

# Check whether kvdo or uds is loaded, and if so attempt to remove it.  A
# failure here means there is still something using the module, which should be
# cleared up before attempting to remove again.
for module in kvdo uds; do
  if grep -q "^${module}" /proc/modules; then
    modprobe -r ${module}
  fi
done

%postun
modules=( $(cat /var/run/rpm-kmod-%{kmod_name}-modules) )
rm /var/run/rpm-kmod-%{kmod_name}-modules
printf '%s\n' "${modules[@]}" | %{sbindir}/weak-modules --remove-modules

%files
%defattr(644,root,root,755)
/lib/modules/%{kmod_headers_version}
/etc/depmod.d/%{kmod_name}.conf
/usr/share/doc/kmod-%{kmod_name}/greylist.txt

%prep
%setup -n %{kmod_name}-%{commit}
%{nil}
set -- *
mkdir source
mv "$@" source/
mkdir obj

%build
rm -rf obj
cp -r source obj
make -C %{kernel_source} M=$PWD/obj/%{kmod_kbuild_dir} V=1 \
	NOSTDINC_FLAGS="-I $PWD/obj/include -I $PWD/obj/include/uapi"
# mark modules executable so that strip-to-file can strip them
find obj/%{kmod_kbuild_dir} -name "*.ko" -type f -exec chmod u+x '{}' +

whitelist="/lib/modules/kabi-current/kabi_whitelist_%{_target_cpu}"
for modules in $( find obj/%{kmod_kbuild_dir} -name "*.ko" -type f -printf "%{findpat}\n" | sed 's|\.ko$||' | sort -u ) ; do
	# update depmod.conf
	module_weak_path=$(echo $modules | sed 's/[\/]*[^\/]*$//')
	if [ -z "$module_weak_path" ]; then
		module_weak_path=%{name}
	else
		module_weak_path=%{name}/$module_weak_path
	fi
	echo "override $(echo $modules | sed 's/.*\///') $(echo %{kmod_headers_version} | sed 's/\.[^\.]*$//').* weak-updates/$module_weak_path" >> source/depmod.conf

	# update greylist
	nm -u obj/%{kmod_kbuild_dir}/$modules.ko | sed 's/.*U //' |  sed 's/^\.//' | sort -u | while read -r symbol; do
		grep -q "^\s*$symbol\$" $whitelist || echo "$symbol" >> source/greylist
	done
done
sort -u source/greylist | uniq > source/greylist.txt

%install
export INSTALL_MOD_PATH=$RPM_BUILD_ROOT
export INSTALL_MOD_DIR=extra/%{name}
make -C %{kernel_source} modules_install V=1 \
	M=$PWD/obj/%{kmod_kbuild_dir}
# Cleanup unnecessary kernel-generated module dependency files.
find $INSTALL_MOD_PATH/lib/modules -iname 'modules.*' -exec rm {} \;

install -m 644 -D source/depmod.conf $RPM_BUILD_ROOT/etc/depmod.d/%{kmod_name}.conf
install -m 644 -D source/greylist.txt $RPM_BUILD_ROOT/usr/share/doc/kmod-%{kmod_name}/greylist.txt
%if 0
%{FIRMWARE_FILES_INSTALL}
%endif
%if 0%{kmod_devel_package}
install -m 644 -D $PWD/obj/%{kmod_kbuild_dir}/Module.symvers $RPM_BUILD_ROOT/usr/share/kmod-%{kmod_name}/Module.symvers
%endif

%clean
rm -rf $RPM_BUILD_ROOT

%changelog
* Sat Jul 21 2018 - Andy Walsh <awalsh@redhat.com> - 6.1.0.181-17
- Fixed a bug which would cause kernel panics when a VDO device is stacked on a
  RAID50 device.
- Resolves: rhbz#1599668
- Fixed a bug which could cause data loss when discarding unused portions of a
  VDO's logical space.
- Resolves: rhbz#1600058
- Modified grow physical to fail in the prepare step if the size isn't
  changing, avoiding a suspend-and-resume cycle.
- Resolves: rhbz#1600662
- Fixed a bug which would cause attempts to grow the physical size of a VDO
  device to fail if the device below the VDO was resized while the VDO was
  offline.
- Resolves: rhbz#1591180

* Mon Jun 11 2018 - Andy Walsh <awalsh@redhat.com> - 6.1.0.171-17
- Bumped NVR to maintain kABI compatibility.
- Resolves: rhbz#1578421

* Sat May 19 2018 - Andy Walsh <awalsh@redhat.com> - 6.1.0.171-16
- Fixed a bug which prevented disabling of the UDS index.
- Resolves: rhbz#1578421

* Sun Apr 29 2018 - Andy Walsh <awalsh@redhat.com> - 6.1.0.168-16
- Updated source to use GitHub
- Fixed module version checking for upgrades.
- Removed debug kernel requirement from spec file.
- Fixed a deadlock resulting from sleeping while holding a spinlock while
  getting statistics.
- Resolves: rhbz#1567742
- Fixed bugs arising from attempts to access sysfs nodes during startup and
  shutdown.
- Resolves: rhbz#1567744
- Removed the prepare_ioctl() function to avoid signature changes since this
  function currently does nothing.
- Resolves: rhbz#1572494

* Tue Feb 27 2018 - Andy Walsh <awalsh@redhat.com> - 6.1.0.153-15
- Fixed preun handling of loaded modules
- Resolves: rhbz#1549178

* Fri Feb 16 2018 - Joseph Chapman <jochapma@redhat.com> - 6.1.0.149-13
- Sync mode is safe if underlying storage changes to requiring flushes
- Resolves: rhbz#1540777

* Wed Feb 07 2018 - Joseph Chapman <jochapma@redhat.com> - 6.1.0.146-13
- Module target is now "vdo" instead of "dedupe"
- Fixed a bug where crash recovery led to failed kernel page request
- Improved modification log messages
- Improved package description and summary fields
- Resolves: rhbz#1535127
- Resolves: rhbz#1535597
- Resolves: rhbz#1540696
- Resolves: rhbz#1541409

* Tue Feb 06 2018 - Andy Walsh <awalsh@redhat.com> - 6.1.0.144-13
- Updated summary and descriptions
- Resolves: rhbz#1541409

* Thu Feb 01 2018 - Joseph Chapman <jochapma@redhat.com> - 6.1.0.130-12
- Fix General Protection Fault unlocking UDS callback mutex
- Removing kmod-kvdo package unloads kernel module
- Fix URL to point to GitHub tree
- Resolves: rhbz#1510176
- Resolves: rhbz#1533260
- Resolves: rhbz#1539061

* Fri Jan 19 2018 - Joseph Chapman <jochapma@redhat.com> - 6.1.0.124-11
- Fixed provisional referencing for dedupe.
- Only log a bio submission from a VDO to itself.
- vdoformat cleans up metadata properly after fail.
- Resolves: rhbz#1511587
- Resolves: rhbz#1520972
- Resolves: rhbz#1532481

* Wed Jan 10 2018 - Joseph Chapman <jochapma@redhat.com> - 6.1.0.114-11
- /sys/uds permissions now resticted to superuser only
- Remove /sys/uds files that should not be used in production
- Removing kvdo module reports version
- VDO automatically chooses the proper write policy by default
- Fixed a Coverity-detected error path leak
- Resolves: rhbz#1525305
- Resolves: rhbz#1527734
- Resolves: rhbz#1527737
- Resolves: rhbz#1527924
- Resolves: rhbz#1528399

* Thu Dec 21 2017 - Joseph Chapman <jochapma@redhat.com> - 6.1.0.106-11
- Detect journal overflow after 160E of writes
- Clean up UDS threads when removing last VDO
- Resolves: rhbz#1512968
- Resolves: rhbz#1523240

* Tue Dec 12 2017 Joe Chapman <jochapma@redhat.com> 6.1.0.97-11
- Default logical size is no longer over-provisioned
- Remove debug logging when verifying dedupe advice
- Resolves: rhbz#1519330

* Fri Dec 08 2017 Joe Chapman <jochapma@redhat.com> 6.1.0.89-11
- improve metadata cleanup after vdoformat failure
- log REQ_FLUSH & REQ_FUA at level INFO
- improve performance of cuncurrent write requests with the same data
- Resolves: rhbz#1520972
- Resolves: rhbz#1521200

* Fri Dec 01 2017 Joe Chapman <jochapma@redhat.com> 6.1.0.72-10
- clear VDO metadata on a vdo remove call
- fix create of new dedupe indices
- add magic number to VDO geometry block
- do less logging when stopping a VDO
- add a UUID
- Resolves: rhbz#1512127
- Resolves: rhbz#1516081
- Resolves: rhbz#1511109
- Resolves: rhbz#1515183

* Fri Nov 17 2017 Joe Chapman <jochapma@redhat.com> 6.1.0.55-9
- fail loading an uncreated index more gracefully
- remove spurious/unnecessary files from the distribution
- fix kernel module version
- make logging less chatty
- fix an integer overflow in makeVDOLayout
- Resolves: rhbz#1511034
- Resolves: rhbz#1511109
- Resolves: rhbz#1511096

* Fri Nov 10 2017 Joe Chapman <jochapma@redhat.com> 6.1.0.44-8
- fix readCacheSize handling large numbers
- vdoformat signals error when it finds a geometry block
- prevent kernel oops when loading an old geometry block
- vdoformat silently rounds down physical sizes to a block boundary
- UDS threads identify related VDO device
- clean up contents of source tarballs
- Resolves: rhbz#1505936
- Resolves: rhbz#1507996
- Resolves: rhbz#1509466
- Resolves: rhbz#1510558
- Resolves: rhbz#1510585
- Resolves: rhbz#1511201
- Resolves: rhbz#1511209

* Fri Nov 03 2017 Joe Chapman <jochapma@redhat.com> 6.1.0.34-7
- Bugfixes
- Resolves: rhbz#1491422

* Mon Oct 30 2017 Joe Chapman <jochapma@redhat.com> 6.1.0.13-6
- Fixed some scanning tool complaints
- Resolves: rhbz#1491422

* Tue Oct 24 2017 Andy Walsh <awalsh@redhat.com> 6.1.0.0-6
- Fixed kernel requirement to allow subsequent releases without updating spec
- Resolves: rhbz#1491422

* Fri Oct 20 2017 John Wiele <jwiele@redhat.com> 6.1.0.0-5
- Bumped kernel requirement to 3.10.0-741
- Resolves: rhbz#1491422

* Tue Oct 17 2017 John Wiele <jwiele@redhat.com> 6.1.0.0-4
- Resolved some missing symbols
- Resolves: rhbz#1491422

* Mon Oct 16 2017 John Wiele <jwiele@redhat.com> 6.1.0.0-3
- Updated to provide a useable package
- Resolves: rhbz#1491422

* Sat Oct 14 2017 Andy Walsh <awalsh@redhat.com> 6.1.0.0-2
- Removed invalid requirement and some unnecessary comments in spec
- Resolves: rhbz#1491422

* Wed Oct 11 2017 John Wiele <jwiele@redhat.com> 6.1.0.0-1
- Initial vdo module for Driver Update Program
- Resolves: rhbz#1491422
