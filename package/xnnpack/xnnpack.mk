################################################################################
#
# xnnpack
#
################################################################################

XNNPACK_VERSION = 74f892c492a8ca5733b8d7e9e96524be6e80ee1c
XNNPACK_SITE = $(call github,google,XNNPACK,$(XNNPACK_VERSION))
XNNPACK_LICENSE = BSD-3-Clause
XNNPACK_LICENSE_FILES = LICENSE
XNNPACK_INSTALL_STAGING = YES
XNNPACK_DEPENDENCIES = cpuinfo fp16 fxdiv pthreadpool
XNNPACK_CONF_OPTS = \
	-DXNNPACK_BUILD_TESTS=OFF \
	-DXNNPACK_BUILD_BENCHMARKS=OFF \
	-DXNNPACK_USE_SYSTEM_LIBS=ON

ifeq ($(BR2_aarch64):$(BR2_TOOLCHAIN_GCC_AT_LEAST_10),y:)
XNNPACK_CONF_OPTS += -DXNNPACK_ENABLE_ARM_BF16=OFF
endif

$(eval $(cmake-package))
