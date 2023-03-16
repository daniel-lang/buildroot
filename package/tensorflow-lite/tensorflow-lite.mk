################################################################################
#
# tensorflow-lite
#
################################################################################

TENSORFLOW_LITE_VERSION = 2.13.0
TENSORFLOW_LITE_SITE =  $(call github,tensorflow,tensorflow,v$(TENSORFLOW_LITE_VERSION))
TENSORFLOW_LITE_INSTALL_STAGING = YES
TENSORFLOW_LITE_LICENSE = Apache-2.0
TENSORFLOW_LITE_LICENSE_FILES = LICENSE
TENSORFLOW_LITE_CPE_ID_VENDOR = google
TENSORFLOW_LITE_CPE_ID_PRODUCT = tensorflow
TENSORFLOW_LITE_CPE_ID_SW_EDITION = lite
TENSORFLOW_LITE_SUBDIR = tensorflow/lite
TENSORFLOW_LITE_SUPPORTS_IN_SOURCE_BUILD = NO
TENSORFLOW_LITE_DEPENDENCIES += \
	host-pkgconf \
	host-flatbuffers \
	cpuinfo \
	eigen \
	farmhash \
	fft2d \
	flatbuffers \
	gemmlowp \
	libabseil-cpp \
	neon-2-sse \
	pthreadpool

TENSORFLOW_LITE_CONF_OPTS = \
	-Dabsl_DIR=$(STAGING_DIR)/usr/lib/cmake/absl \
	-DBUILD_SHARED_LIBS=ON \
	-DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON \
	-DCMAKE_POSITION_INDEPENDENT_CODE=ON \
	-DEigen3_DIR=$(STAGING_DIR)/usr/share/eigen3/cmake \
	-DFETCHCONTENT_FULLY_DISCONNECTED=ON \
	-DFETCHCONTENT_QUIET=OFF \
	-DFFT2D_SOURCE_DIR=$(STAGING_DIR)/usr/include/fft2d \
	-DFlatBuffers_DIR=$(STAGING_DIR)/usr/lib/cmake/flatbuffers \
	-Dgemmlowp_DIR=$(STAGING_DIR)/usr/lib/cmake/gemmlowp \
	-DNEON_2_SSE_DIR=$(STAGING_DIR)/usr/lib/cmake/NEON_2_SSE \
	-DSYSTEM_FARMHASH=ON \
	-DSYSTEM_PTHREADPOOL=ON \
	-DTFLITE_ENABLE_EXTERNAL_DELEGATE=ON \
	-DTFLITE_ENABLE_GPU=OFF \
	-DTFLITE_ENABLE_INSTALL=ON \
	-DTFLITE_ENABLE_MMAP=ON \
	-DTFLITE_ENABLE_NNAPI=OFF

ifeq ($(BR2_PACKAGE_RUY),y)
TENSORFLOW_LITE_DEPENDENCIES += ruy
TENSORFLOW_LITE_CONF_OPTS += -DTFLITE_ENABLE_RUY=ON
else
TENSORFLOW_LITE_CONF_OPTS += -DTFLITE_ENABLE_RUY=OFF
endif

ifeq ($(BR2_PACKAGE_XNNPACK),y)
TENSORFLOW_LITE_DEPENDENCIES += xnnpack
TENSORFLOW_LITE_CONF_OPTS += -DTFLITE_ENABLE_XNNPACK=ON -Dxnnpack_POPULATED=ON
else
TENSORFLOW_LITE_CONF_OPTS += -DTFLITE_ENABLE_XNNPACK=OFF
endif

ifeq ($(BR2_PACKAGE_TENSORFLOW_LITE_BUILD_EXAMPLE),y)
define TENSORFLOW_LITE_EXAMPLE_BUILD_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(TENSORFLOW_LITE_BUILDDIR) label_image
endef

define TENSORFLOW_LITE_EXAMPLE_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(TENSORFLOW_LITE_BUILDDIR)/examples/label_image/label_image $(TARGET_DIR)/usr/bin/label_image
endef
endif

TENSORFLOW_LITE_POST_BUILD_HOOKS += TENSORFLOW_LITE_EXAMPLE_BUILD_CMDS
TENSORFLOW_LITE_POST_INSTALL_TARGET_HOOKS += TENSORFLOW_LITE_EXAMPLE_INSTALL_TARGET_CMDS

$(eval $(cmake-package))
