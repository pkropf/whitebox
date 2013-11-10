#include <linux/dma-mapping.h>

#include "whitebox.h"
#include "whitebox_block.h"

#include "pdma.h"

static int whitebox_rf_sink_debug = 0;
#define d_printk(level, fmt, args...)				\
	if (whitebox_rf_sink_debug >= level) printk(KERN_INFO "%s: " fmt,	\
					__func__, ## args)

void whitebox_rf_sink_init(struct whitebox_rf_sink *rf_sink,
        int dma_ch, void (*dma_cb)(void*), void *dma_cb_data,
        struct whitebox_exciter *exciter)
{
    spin_lock_init(&rf_sink->lock);
    rf_sink->off = 0;
    rf_sink->dma_ch = dma_ch;
    rf_sink->dma_cb = dma_cb;
    rf_sink->dma_cb_data = dma_cb_data;
    rf_sink->exciter = exciter;
}

int whitebox_rf_sink_alloc(struct whitebox_rf_sink *rf_sink)
{
    return pdma_request(rf_sink->dma_ch,
            (pdma_irq_handler_t)rf_sink->dma_cb,
            rf_sink->dma_cb_data,
            10,
            rf_sink->exciter->pdma_config);
}

void whitebox_rf_sink_free(struct whitebox_rf_sink *rf_sink)
{
    pdma_release(rf_sink->dma_ch);
}

size_t whitebox_rf_sink_space_available(struct whitebox_rf_sink *rf_sink,
        unsigned long *dest)
{
    return rf_sink->exciter->ops->space_available(rf_sink->exciter, dest);
}

int whitebox_rf_sink_produce(struct whitebox_rf_sink *rf_sink, size_t count)
{
    rf_sink->off += count;
    return 0;
}

int whitebox_rf_sink_work(struct whitebox_rf_sink *rf_sink,
        unsigned long src, size_t src_count,
        unsigned long dest, size_t dest_count)
{
    rf_sink->dma_count = min(src_count, dest_count);
    rf_sink->dma_mapping = dma_map_single(NULL,
            (void*)src, rf_sink->dma_count, DMA_TO_DEVICE);
    if (dma_mapping_error(NULL, rf_sink->dma_mapping)) {
        d_printk(0, "failed to map dma\n");
        return -EFAULT;
    }

    pdma_start(rf_sink->dma_ch,
            rf_sink->dma_mapping,
            dest,
            rf_sink->dma_count >> 2);
    return 0;
}

int whitebox_rf_sink_work_done(struct whitebox_rf_sink *rf_sink)
{
    dma_unmap_single(NULL, rf_sink->dma_mapping,
            rf_sink->dma_count, DMA_TO_DEVICE);
    return (int)rf_sink->dma_count;
}