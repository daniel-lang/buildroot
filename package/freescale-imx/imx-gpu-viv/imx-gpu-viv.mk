################################################################################
#
# imx-gpu-viv
#
################################################################################

ifeq ($(BR2_aarch64),y)
IMX_GPU_VIV_VERSION = 6.4.3.p4.4-aarch64
else
IMX_GPU_VIV_VERSION = 6.4.3.p4.4-aarch32
endif
IMX_GPU_VIV_SITE = $(FREESCALE_IMX_SITE)
IMX_GPU_VIV_SOURCE = imx-gpu-viv-$(IMX_GPU_VIV_VERSION).bin

IMX_GPU_VIV_INSTALL_STAGING = YES

IMX_GPU_VIV_LICENSE = NXP Semiconductor Software License Agreement
IMX_GPU_VIV_LICENSE_FILES = EULA COPYING
IMX_GPU_VIV_REDISTRIBUTE = NO

IMX_GPU_VIV_PROVIDES = libegl libgles libopencl libopenvg

ifeq ($(BR2_aarch64),y)
IMX_GPU_VIV_PROVIDES += libgbm
endif

IMX_GPU_VIV_LIB_TARGET = $(call qstrip,$(BR2_PACKAGE_IMX_GPU_VIV_OUTPUT))

ifeq ($(BR2_PACKAGE_IMX_GPUG_VIV_USES_WAYLAND),y)
IMX_GPU_VIV_DEPENDENCIES += libdrm wayland
IMX_GPU_VIV_OUTPUT_DIR = wayland
else
IMX_GPU_VIV_OUTPUT_DIR = fb
endif

define IMX_GPU_VIV_EXTRACT_CMDS
	$(call NXP_EXTRACT_HELPER,$(IMX_GPU_VIV_DL_DIR)/$(IMX_GPU_VIV_SOURCE))
endef

# The package comes with multiple versions of egl.pc,
# depending on the output the original egl.pc is replaced
# with a symlink:
# - arm/frambuffer: symlink to egl_linuxfb.pc
# - aarch64/framebuffer: original egl.pc without a symlink
# - wayland: symblink to egl_wayland.pc
ifeq ($(IMX_GPU_VIV_LIB_TARGET)$(BR2_arm),fby)
define IMX_GPU_VIV_FIXUP_PKGCONFIG
	ln -sf egl_linuxfb.pc $(@D)/gpu-core/usr/lib/pkgconfig/egl.pc
endef
else ifeq ($(IMX_GPU_VIV_LIB_TARGET),wayland)
define IMX_GPU_VIV_FIXUP_PKGCONFIG
	ln -sf egl_wayland.pc $(@D)/gpu-core/usr/lib/pkgconfig/egl.pc
endef
endif

IMX_GPU_VIV_PLATFORM_DIR = $(call qstrip,$(BR2_PACKAGE_IMX_GPU_VIV_PLATFORM))
ifneq ($(IMX_GPU_VIV_PLATFORM_DIR),)
define IMX_GPU_VIV_COPY_PLATFORM
	cp -dpfr $(@D)/gpu-core/usr/lib/$(IMX_GPU_VIV_PLATFORM_DIR)/* $(@D)/gpu-core/usr/lib/
endef
endif

# Instead of building, we fix up the inconsistencies that exist
# in the upstream archive here. We also remove unused backend files.
# Make sure these commands are idempotent.
define IMX_GPU_VIV_BUILD_CMDS
	cp -dpfr $(@D)/gpu-core/usr/lib/$(IMX_GPU_VIV_OUTPUT_DIR)/* $(@D)/gpu-core/usr/lib/
	$(foreach backend,fb wayland, \
		$(RM) -r $(@D)/gpu-core/usr/lib/$(backend)
	)
	$(IMX_GPU_VIV_COPY_PLATFORM)
	$(foreach platform,mx8mn mx8mp mx8mq mx8qm mx8qxp mx8ulp, \
		$(RM) -r $(@D)/gpu-core/usr/lib/$(platform)
	)
	$(IMX_GPU_VIV_FIXUP_PKGCONFIG)
endef

define IMX_GPU_VIV_INSTALL_STAGING_CMDS
	cp -r $(@D)/gpu-core/usr/* $(STAGING_DIR)/usr
endef

ifeq ($(BR2_PACKAGE_IMX_GPU_VIV_EXAMPLES),y)
define IMX_GPU_VIV_INSTALL_EXAMPLES
	mkdir -p $(TARGET_DIR)/usr/share/examples/
	cp -r $(@D)/gpu-demos/opt/* $(TARGET_DIR)/usr/share/examples/
endef
endif

ifeq ($(BR2_PACKAGE_IMX_GPU_VIV_GMEM_INFO),y)
define IMX_GPU_VIV_INSTALL_GMEM_INFO
	cp -dpfr $(@D)/gpu-tools/gmem-info/usr/bin/* $(TARGET_DIR)/usr/bin/
endef
endif

define IMX_GPU_VIV_INSTALL_TARGET_CMDS
	$(IMX_GPU_VIV_INSTALL_EXAMPLES)
	$(IMX_GPU_VIV_INSTALL_GMEM_INFO)
	cp -a $(@D)/gpu-core/usr/lib $(TARGET_DIR)/usr
	$(INSTALL) -D -m 0644 $(@D)/gpu-core/etc/Vivante.icd $(TARGET_DIR)/etc/OpenCL/vendors/Vivante.icd
endef

$(eval $(generic-package))
