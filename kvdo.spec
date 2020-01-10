%global commit                  7e17a12d177a2a0fa68d9f490a1cc937ffab9d93
%global gittag                  6.1.2.41
%global shortcommit             %(c=%{commit}; echo ${c:0:7})
%define spec_release            5

%define kmod_name		kvdo
%define kmod_driver_version	%{gittag}
%define kmod_rpm_release	%{spec_release}
%define kmod_kernel_version	3.10.0-1025.el7
%define kmod_headers_version	%(rpm -qa kernel-devel | sed 's/^kernel-devel-//')
%define kmod_kbuild_dir		.
%define kmod_dependencies       %{nil}
%define kmod_build_dependencies	%{nil}
%define kmod_devel_package	0

Source0:	https://github.com/dm-vdo/%{kmod_name}/archive/%{commit}/%{kmod_name}-%{shortcommit}.tar.gz
%{nil}

%define findpat %( echo "%""P" )
%define __find_requires /usr/lib/rpm/redhat/find-requires.ksyms
%if 0%{?rhel}
# Fedora has deprecated this.
%define __find_provides /usr/lib/rpm/redhat/find-provides.ksyms %{kmod_name} %{?epoch:%{epoch}:}%{version}-%{release}
%endif
%define sbindir %( if [ -d "/sbin" -a \! -h "/sbin" ]; then echo "/sbin"; else echo %{_sbindir}; fi )

Name:		kmod-kvdo
Version:	%{kmod_driver_version}
Release:	%{kmod_rpm_release}%{?dist}
Summary:	Kernel Modules for Virtual Data Optimizer
License:	GPLv2+
URL:		http://github.com/dm-vdo/kvdo
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
%if 0%{?fedora}
# Fedora requires elfutils-libelf-devel, while rhel does not.
BuildRequires:  elfutils-libelf-devel
%endif
BuildRequires:	glibc
%if 0%{?rhel}
# Fedora doesn't have abi whitelists.
BuildRequires:	kernel-abi-whitelists
%endif
BuildRequires:	kernel-devel >= %{kmod_kernel_version}
BuildRequires:  kernel-debug >= %{kmod_kernel_version}
BuildRequires:  libuuid-devel
BuildRequires:  redhat-rpm-config
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

%pre
# During the install, check whether kvdo or uds is loaded.  A warning here
# indicates that a previous install was not completely removed.  This message
# is purely informational to the user.
for module in kvdo uds; do
  if grep -q "^${module}" /proc/modules; then
    if [ "${module}" == "kvdo" ]; then
      echo "WARNING: Found ${module} module previously loaded (Version: $(cat /sys/kvdo/version 2>/dev/null || echo Uknown)).  A reboot is recommended before attempting to use the newly installed module."
    else
      echo "WARNING: Found ${module} module previously loaded.  A reboot is recommended before attempting to use the newly installed module."
    fi
  fi
done

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
# failure to unload means there is still something using the module.  To make
# sure the user is aware, we print a warning with recommended instructions.
for module in kvdo uds; do
  if grep -q "^${module}" /proc/modules; then
    warnMessage="WARNING: ${module} in use.  Changes will take effect after a reboot."
    modprobe -r ${module} 2>/dev/null || echo ${warnMessage} && /usr/bin/true
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
* Wed Mar 27 2019 - Andy Walsh <awalsh@redhat.com> 6.1.2.41-5
- Reduced and rate limited error logging in order to avoid kernel soft-lockups.
  - Resolves: rhbz#1687005

* Tue Mar 19 2019 - Andy Walsh <awalsh@redhat.com> 6.1.2.38-5
- Fixed more error path memory leaks.
  - Resolves: rhbz#1609426
- Rebased to version 6.2.0 of the UDS module
  - Resolves: rhbz#1637762
- Improved counting of dedupe timeouts by including in the count queries
  which are not made due to their being a lack of resources from previous
  queries taking too long.
  - Resolves: rhbz#1639898
- Fixed a NULL pointer dereference if dmeventd registration fails.
  - Resolves: rhbz#1640794
- Fixed a bug in the statistics tracking partial I/Os.
  - Resolves: rhbz#1594406
- Allowed VDO backing devices to be specified by major:minor device number.
  - Resolves: rhbz#1637762
- Suppressed egregious read-only error logging.
  - Resolves: rhbz#1687005

* Tue Sep 18 2018 - Andy Walsh <awalsh@redhat.com> 6.1.1.125-5
- Adjusted the warning when modules are found during install.
- Resolves: rhbz#1553420

* Fri Sep 14 2018 - Andy Walsh <awalsh@redhat.com> 6.1.1.125-4
- Attempt to unload modules and print a warning if unable to.
- Resolves: rhbz#1553420
- Fixed a hang when recovering a VDO volume with a physical size larger than
  16TB.
- Resolves: rhbz#1628316

* Wed Sep 05 2018 - Andy Walsh <awalsh@redhat.com> 6.1.1.120-3
- Rebuilt to work with kernel build
- Resolves: rhbz#1625555

* Sun Jul 29 2018 - Andy Walsh <awalsh@redhat.com> 6.1.1.120-2
- No longer attempt to unload modules in %preun
- Resolves: rhbz#1553420
- Improved memory allocation by not using the incorrect __GFP_NORETRY flag
  and by using the memalloc_noio_save mechanism.
- Resolves: rhbz#1571292
- Fixed a potential deadlock in the UDS index by using the kernel supplied
  struct callback instead of our own implementation of synchronous
  callbacks.
- Resolves: rhbz#1602151
- Fixed a potential stack overflow when reaping the recovery journal.
- Resolves: rhbz#1608070
- No longer attempt to unload modules in %preun
- Resolves: rhbz#1553420
- Improved safety around memory allocation permissions
- Resolves: rhbz#1595923
- Improved statistics accounting to allow for concurrent dedupe.
- Resolves: rhbz#1540722

* Sun Jul 15 2018 - Andy Walsh <awalsh@redhat.com> 6.1.1.111-1
- Added support for issuing fullness warnings via dmeventd
- rhbz#1519307
- Fixed a bug which would cause kernel panics when a VDO device is stacked on a
  RAID50 device.
- Resolves: rhbz#1593444
- Improved logging when growing the physical size of a VDO volume.
- Resolves: rhbz#1597890
- Resolves: rhbz#1597886
- Removed misleading log messages when rebuilding the UDS index.
- Resolves: rhbz#1599867

* Wed Jun 20 2018 - Andy Walsh <awalsh@redhat.com> 6.1.1.99-1
- Added /sys/kvdo/version which contains the currently loaded version of
  the kvdo module.
- Resolves: rhbz#1533950
- Added logging of normal operation when a VDO device starts normally.
- Resolves: rhbz#1520988
- Fixed a race in the UDS module which could cause the index to go offline.
- Resolves: rhbz#1520988
- Fixed a bug which would cause attempts to grow the physical size of a VDO
  device to fail if the device below the VDO was resized while the VDO was
  offline.
- Resolves: rhbz#1582647
- Fixed thread safety issues in the UDS page cache.
- Resolves: rhbz#1579492
- Modified the vdo script to not allow creation of a VDO device on top of an
  already running VDO device.
- Resolves: rhbz#1572640
- Fixed a bug which could cause data loss when discarding unused portions of a
  VDO's logical space.
- Resolves: rhbz#1589249
- Modified grow physical to fail in the prepare step if the size isn't
  changing, avoiding a suspend-and-resume cycle.
- Resolves: rhbz#1576539

* Fri May 11 2018 - Andy Walsh <awalsh@redhat.com> - 6.1.1.84-1
- Deleted unused UDS features.
- Improved performance of sub 4K writes.
- Simplified and improved performance of writes with FUA.
- Improved the accuracy of dedupe statistics.
- Made the MurmurHash3 implementation architecture independent.
- Fixed compilation errors on newer versions of GCC.
- Eliminated spurious allocation of a UDS sparse cache for dense indexes.
- Fixed a deadlock resulting from sleeping while holding a spinlock while
  getting statistics.
- Resvolves: rhbz#1562228
- Fixed bugs related to the timing of the creation and destruction of sysfs
  nodes relative to the creation and destruction of VDO data structures.
- Resolves: rhbz#1559692
- Fixed a bug which made deduplication impossible to disable.
- Removed obsolete code.
- Improved deduplication of concurrent requests containing the same data.
- Reduced unnecessary logging.
- Resolves: rhbz#1511127
- Removed the prepare_ioctl() function to avoid signature changes since
  this function currently does nothing.
- Resolves: rhbz#1568129
- Fixed a bug which made using a sparse index impossible to create.
- Resolves: rhbz#1570156

* Thu May 10 2018 - Andy Walsh <awalsh@redhat.com> - 6.1.1.24-1
- Rebased to 6.1.1 branch from github
- Resolves: rhbz#1576701
- Improved some error messages

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
