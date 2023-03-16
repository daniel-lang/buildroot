################################################################################
#
# ruy
#
################################################################################

RUY_VERSION = 32dd2b92622102b1309754ac5aa61c1a581dd194
RUY_SITE = $(call github,google,ruy,$(RUY_VERSION))
RUY_LICENSE = Apache-2.0
RUY_LICENSE_FILES = LICENSE
RUY_INSTALL_STAGING = YES
RUY_DEPENDENCIES = cpuinfo
RUY_CONF_OPTS = \
	-DCMAKE_POSITION_INDEPENDENT_CODE=ON \
	-DRUY_FIND_CPUINFO=ON \
	-DRUY_MINIMAL_BUILD=ON

$(eval $(cmake-package))
