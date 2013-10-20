#ifndef __WHITEBOX_H
#define __WHITEBOX_H

#include <linux/mutex.h>
#include <linux/platform_device.h>
#include <linux/types.h>
#include <linux/wait.h>

#include "whitebox_ioctl.h"

#define WHITEBOX_DRIVER_NAME "whitebox"

#define WHITEBOX_EXCITER_REGS          0x40050400
#define WHITEBOX_EXCITER_SAMPLE_OFFSET 0x00
#define WHITEBOX_EXCITER_STATUS_OFFSET 0x04
#define WHITEBOX_EXCITER_INTERP_OFFSET 0x08
#define WHITEBOX_EXCITER_FCW_OFFSET    0x0c
#define WHITEBOX_EXCITER_REGS_COUNT    0x10

#define WHITEBOX_CMX991_REGS_READ_BASE  0xe1
#define WHITEBOX_CMX991_REGS_WRITE_BASE 0x11
#define WHITEBOX_CMX991_LD_REG          0xd1
#define WHITEBOX_CMX991_LD_MASK         0x40

/*
 * These whitebox pin to Linux kernel GPIO mappings are derived from the
 * Whitebox Libero SmartDesign.  */
#define FPGA_GPIO_BASE 32
#define WHITEBOX_GPIO_ADC_S2       (FPGA_GPIO_BASE+3)
#define WHITEBOX_GPIO_ADC_S1       (FPGA_GPIO_BASE+4)
#define WHITEBOX_GPIO_ADC_DFS      (FPGA_GPIO_BASE+5)
#define WHITEBOX_GPIO_DAC_EN       (FPGA_GPIO_BASE+6)
#define WHITEBOX_GPIO_DAC_PD       (FPGA_GPIO_BASE+7)
#define WHITEBOX_GPIO_DAC_CS       (FPGA_GPIO_BASE+8)
#define WHITEBOX_GPIO_RADIO_RESETN (FPGA_GPIO_BASE+9)
#define WHITEBOX_GPIO_RADIO_CDATA  (FPGA_GPIO_BASE+10)
#define WHITEBOX_GPIO_RADIO_SCLK   (FPGA_GPIO_BASE+11)
#define WHITEBOX_GPIO_RADIO_RDATA  (FPGA_GPIO_BASE+12)
#define WHITEBOX_GPIO_RADIO_CSN    (FPGA_GPIO_BASE+13)
#define WHITEBOX_GPIO_VCO_CLK      (FPGA_GPIO_BASE+14)
#define WHITEBOX_GPIO_VCO_DATA     (FPGA_GPIO_BASE+15)
#define WHITEBOX_GPIO_VCO_LE       (FPGA_GPIO_BASE+16)
#define WHITEBOX_GPIO_VCO_CE       (FPGA_GPIO_BASE+17)
#define WHITEBOX_GPIO_VCO_PDB      (FPGA_GPIO_BASE+18)
#define WHITEBOX_GPIO_VCO_LD       (FPGA_GPIO_BASE+19)


/*
 * Platform data includes pin mappings for each GPIO on the Bravo card
 */
struct whitebox_platform_data_t {
    unsigned adc_s1_pin;
    unsigned adc_s2_pin;
    unsigned adc_dfs_pin;
    unsigned dac_en_pin;
    unsigned dac_pd_pin;
    unsigned dac_cs_pin;
    unsigned radio_resetn_pin;
    unsigned radio_cdata_pin;
    unsigned radio_sclk_pin;
    unsigned radio_rdata_pin;
    unsigned radio_csn_pin;
    unsigned vco_clk_pin;
    unsigned vco_data_pin;
    unsigned vco_le_pin;
    unsigned vco_ce_pin;
    unsigned vco_pdb_pin;
    unsigned vco_ld_pin;
    u8 tx_dma_ch;
};

#define WHITEBOX_PLATFORM_DATA(pdev) ((struct whitebox_platform_data_t *)(pdev->dev.platform_data))

#endif /* __WHITEBOX_H */