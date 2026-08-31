/* Six/22-channel glove acquisition. No robot control. See STM32/TIMING.md. */
#include "stm32f10x.h"
#include "glove_config.h"
#include "glove_protocol.h"
#include <string.h>

static volatile uint32_t timer_high, tick_seq, due_seq;
static volatile uint8_t sample_due, sampling;
static volatile uint16_t missed, rx_errors;
static volatile uint16_t tx_drops;
static volatile uint32_t session;
static uint8_t tx_buffer[GLOVE_FRAME_BYTES], sample_buffer[GLOVE_FRAME_BYTES];
static uint8_t sample_queue[4][GLOVE_FRAME_BYTES];
static volatile uint8_t queue_head, queue_count, tx_active;
static void transmit(void);
static volatile uint8_t rx_packet[64], rx_ready;
static uint8_t rx_buffer[64], rx_count;
static volatile uint32_t rx_time;

/* TIM2 is a 16-bit 1MHz counter extended to 32 bits; wraps every ~71.6min. */
static uint32_t micros(void) {
    uint32_t mask=__get_PRIMASK(), hi, lo;
    __disable_irq();
    hi=timer_high; lo=TIM2->CNT;
    if (TIM2->SR & TIM_FLAG_Update) { hi+=65536u; lo=TIM2->CNT; }
    __set_PRIMASK(mask);
    return hi+lo;
}
void TIM2_IRQHandler(void) {
    if (TIM_GetITStatus(TIM2,TIM_IT_Update)!=RESET) {
        TIM_ClearITPendingBit(TIM2,TIM_IT_Update); timer_high+=65536u;
    }
}
void TIM3_IRQHandler(void) {
    if (TIM_GetITStatus(TIM3,TIM_IT_Update)!=RESET) {
        TIM_ClearITPendingBit(TIM3,TIM_IT_Update);
        ++tick_seq;
        if (sampling || sample_due) ++missed;
        if (!sampling) { due_seq=tick_seq; sample_due=1; }
    }
}
void USART1_IRQHandler(void) {
    uint32_t sr=USART1->SR;
    uint8_t b;
    if (!(sr & (USART_SR_RXNE|USART_SR_ORE|USART_SR_FE|USART_SR_NE|USART_SR_PE))) return;
    b=(uint8_t)USART1->DR;
    if (sr & (USART_SR_ORE|USART_SR_FE|USART_SR_NE|USART_SR_PE)) { ++rx_errors; rx_count=0; return; }
    if (!rx_count && b!=0xaa) return;
    if (rx_count==1 && b!=0x55) { rx_count=(b==0xaa)?1:0; return; }
    rx_buffer[rx_count++]=b;
    if (rx_count==64) {
        uint32_t stamp=micros();
        if (rx_buffer[2]==1 && rx_buffer[3]==2 &&
            glove_crc(rx_buffer+2,60)==((uint16_t)rx_buffer[62]|((uint16_t)rx_buffer[63]<<8))) {
            if (!rx_ready) {
                unsigned i;
                for (i=0;i<64;++i) rx_packet[i]=rx_buffer[i];
                rx_time=stamp; rx_ready=1;
            } else ++rx_errors;
            rx_count=0;
        } else {
            /* Resynchronize after insertion/deletion of bytes, not only clean frames. */
            unsigned i, start=64;
            ++rx_errors;
            for (i=1;i<63;++i) if (rx_buffer[i]==0xaa && rx_buffer[i+1]==0x55) { start=i; break; }
            if (start<64) { rx_count=(uint8_t)(64-start); memmove(rx_buffer,rx_buffer+start,rx_count); }
            else { rx_count=(rx_buffer[63]==0xaa)?1:0; rx_buffer[0]=0xaa; }
        }
    }
}
static void wait_us(uint32_t duration) {
    uint32_t start=micros();
    while ((uint32_t)(micros()-start)<duration) { /* interrupts remain enabled */ }
}
static uint16_t conversion(void) {
    uint32_t start=micros();
    ADC_ClearFlag(ADC1,ADC_FLAG_EOC);
    ADC_SoftwareStartConvCmd(ADC1,ENABLE);
    while (ADC_GetFlagStatus(ADC1,ADC_FLAG_EOC)==RESET)
        if ((uint32_t)(micros()-start)>GLOVE_ADC_TIMEOUT_US) {
            /* An IRQ may have preempted us after the first EOC check.
             * Do not label a conversion which completed during that IRQ as failed. */
            if (ADC_GetFlagStatus(ADC1,ADC_FLAG_EOC)==RESET) return 0xffffu;
            break;
        }
    return ADC_GetConversionValue(ADC1);
}
static uint16_t read_adc(void) {
    uint32_t sum=0; unsigned i; uint16_t v;
    if (conversion()==0xffffu) return 0xffffu;
    for(i=0;i<GLOVE_ADC_AVERAGES;++i) {
        v=conversion(); if(v==0xffffu) return v; sum+=v;
    }
    return (uint16_t)(sum/GLOVE_ADC_AVERAGES); /* 0..4095; no artificial +1 */
}
static void identity(uint8_t *p) {
    const volatile uint32_t *uid=(const volatile uint32_t *)0x1ffff7e8u;
    put32(p,uid[0]); put32(p+4,uid[1]); put32(p+8,uid[2]);
}
static void acquire(uint32_t seq) {
    uint32_t start=micros(), begin, end;
    unsigned i; uint16_t value;
    memset(sample_buffer,0,sizeof(sample_buffer));
    identity(sample_buffer+4);
    put32(sample_buffer+16,session); put32(sample_buffer+20,seq); put32(sample_buffer+24,start);
    for(i=0;i<(GLOVE_CHANNELS==22 ? 8u : 6u);++i) {
        unsigned bank;
        /* U6/U7 share PA5/6/7; U10 uses PA1/2/3. Switch together,
         * wait once, then sample PA0, PB0 and PB1 sequentially. */
        uint32_t bits=((uint32_t)i<<1)&0x0eu;
        uint32_t pins=0x0eu;
#if GLOVE_CHANNELS == 22
        bits|=((uint32_t)i<<5)&0xe0u; pins|=0xe0u;
#endif
        GPIOA->BSRR=((pins & ~bits)<<16)|bits;
        wait_us(GLOVE_MUX_SETTLE_US);
        for(bank=0;bank<(GLOVE_CHANNELS==22 ? 3u : 1u);++bank) {
            unsigned index;
            uint8_t channel;
            if(bank==0) { if(i>=6) continue; index=i; channel=ADC_Channel_0; }
            else { index=6+(bank-1)*8+i; channel=bank==1 ? ADC_Channel_8 : ADC_Channel_9; }
            ADC_RegularChannelConfig(ADC1,channel,1,GLOVE_ADC_SAMPLE_TIME);
            begin=micros(); value=read_adc(); end=micros();
            put16(sample_buffer+32+2*index,(uint16_t)((begin-start)+(uint32_t)(end-begin)/2));
            put16(sample_buffer+32+2*GLOVE_CHANNELS+2*index,value);
        }
    }
    put32(sample_buffer+28,micros());
    put16(sample_buffer+32+4*GLOVE_CHANNELS,missed);
    put16(sample_buffer+34+4*GLOVE_CHANNELS,tx_drops);
    put16(sample_buffer+36+4*GLOVE_CHANNELS,rx_errors);
    seal_frame_size(sample_buffer,GLOVE_CHANNELS==22 ? 4 : 1,GLOVE_FRAME_BYTES);
    {
        uint32_t mask=__get_PRIMASK(); uint8_t tail;
        __disable_irq();
        /* A sync session may have changed in the DMA ISR during this scan. */
        if(get32(sample_buffer+16)!=session) { ++tx_drops; __set_PRIMASK(mask); return; }
        if(queue_count==4) { ++tx_drops; queue_head=(queue_head+1)&3; --queue_count; }
        tail=(queue_head+queue_count)&3;
        memcpy(sample_queue[tail],sample_buffer,GLOVE_FRAME_BYTES); ++queue_count;
        __set_PRIMASK(mask);
    }
}
void DMA1_Channel4_IRQHandler(void) {
    if(DMA_GetITStatus(DMA1_IT_TC4) || DMA_GetITStatus(DMA1_IT_TE4)) {
        if(DMA_GetITStatus(DMA1_IT_TE4)) ++tx_drops;
        DMA_Cmd(DMA1_Channel4,DISABLE); DMA_ClearITPendingBit(DMA1_IT_GL4);
        /* Last byte is already in USART DR: buffer is free; next DMA can queue behind it. */
        tx_active=0; transmit();
    }
}
static void send_buffer(unsigned size) {
    DMA_Cmd(DMA1_Channel4,DISABLE); DMA_ClearFlag(DMA1_FLAG_GL4);
    DMA_SetCurrDataCounter(DMA1_Channel4,size);
    USART_ClearFlag(USART1,USART_FLAG_TC);
    tx_active=1; DMA_Cmd(DMA1_Channel4,ENABLE);
}
static void transmit(void) {
    uint32_t outer_mask=__get_PRIMASK();
    __disable_irq();
    if(tx_active) { __set_PRIMASK(outer_mask); return; }
    if(rx_ready) {
        uint32_t mask=__get_PRIMASK(), t2, req; uint8_t request[64]; unsigned i;
        __disable_irq();
        for(i=0;i<64;++i) request[i]=rx_packet[i];
        t2=rx_time; rx_ready=0; __set_PRIMASK(mask);
        req=get32(request+8);
        if(session!=get32(request+4)) { session=get32(request+4); queue_count=0; queue_head=0; }
        memset(tx_buffer,0,64); identity(tx_buffer+4);
        put32(tx_buffer+16,session); put32(tx_buffer+20,req); put32(tx_buffer+24,t2);
        put32(tx_buffer+28,micros()); /* t3: before CRC and DMA submission */
        seal_frame(tx_buffer,3); send_buffer(64);
    } else if(queue_count) {
        memcpy(tx_buffer,sample_queue[queue_head],GLOVE_FRAME_BYTES);
        queue_head=(queue_head+1)&3; --queue_count; send_buffer(GLOVE_FRAME_BYTES);
    }
    __set_PRIMASK(outer_mask);
}
static void initialize(void) {
    RCC_ClocksTypeDef clocks; GPIO_InitTypeDef gpio; USART_InitTypeDef uart;
    ADC_InitTypeDef adc; DMA_InitTypeDef dma; TIM_TimeBaseInitTypeDef timer;
    uint32_t timer_clock;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA|RCC_APB2Periph_GPIOB|RCC_APB2Periph_ADC1|RCC_APB2Periph_USART1|RCC_APB2Periph_AFIO,ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM2|RCC_APB1Periph_TIM3,ENABLE);
    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_DMA1,ENABLE);
    RCC_GetClocksFreq(&clocks); RCC_ADCCLKConfig(RCC_PCLK2_Div6);
    timer_clock=clocks.PCLK1_Frequency;
    if(clocks.PCLK1_Frequency!=clocks.HCLK_Frequency) timer_clock*=2;
    TIM_TimeBaseStructInit(&timer); timer.TIM_Prescaler=(uint16_t)(timer_clock/1000000u-1);
    timer.TIM_Period=65535; TIM_TimeBaseInit(TIM2,&timer);
    TIM_ClearITPendingBit(TIM2,TIM_IT_Update); TIM_ITConfig(TIM2,TIM_IT_Update,ENABLE);
    NVIC_SetPriority(TIM2_IRQn,0); NVIC_EnableIRQ(TIM2_IRQn); TIM_Cmd(TIM2,ENABLE);
    timer.TIM_Period=1000000u/GLOVE_SAMPLE_HZ-1; TIM_TimeBaseInit(TIM3,&timer);
    TIM_ClearITPendingBit(TIM3,TIM_IT_Update); TIM_ITConfig(TIM3,TIM_IT_Update,ENABLE);
    NVIC_SetPriority(TIM3_IRQn,1); NVIC_EnableIRQ(TIM3_IRQn);
    GPIO_StructInit(&gpio); gpio.GPIO_Pin=GPIO_Pin_9; gpio.GPIO_Mode=GPIO_Mode_AF_PP;
    gpio.GPIO_Speed=GPIO_Speed_50MHz; GPIO_Init(GPIOA,&gpio);
    gpio.GPIO_Pin=GPIO_Pin_10; gpio.GPIO_Mode=GPIO_Mode_IN_FLOATING; GPIO_Init(GPIOA,&gpio);
    gpio.GPIO_Pin=GPIO_Pin_0; gpio.GPIO_Mode=GPIO_Mode_AIN; GPIO_Init(GPIOA,&gpio);
    gpio.GPIO_Pin=GPIO_Pin_1|GPIO_Pin_2|GPIO_Pin_3|GPIO_Pin_7; gpio.GPIO_Mode=GPIO_Mode_Out_PP; GPIO_Init(GPIOA,&gpio);
    GPIO_ResetBits(GPIOA,GPIO_Pin_1|GPIO_Pin_2|GPIO_Pin_3|GPIO_Pin_7);
#if GLOVE_CHANNELS == 22
    gpio.GPIO_Pin=GPIO_Pin_5|GPIO_Pin_6|GPIO_Pin_7; GPIO_Init(GPIOA,&gpio);
    GPIO_ResetBits(GPIOA,GPIO_Pin_5|GPIO_Pin_6|GPIO_Pin_7);
    gpio.GPIO_Pin=GPIO_Pin_0|GPIO_Pin_1; gpio.GPIO_Mode=GPIO_Mode_AIN; GPIO_Init(GPIOB,&gpio);
#endif
    USART_StructInit(&uart); uart.USART_BaudRate=GLOVE_UART_BAUD;
    uart.USART_Mode=USART_Mode_Tx|USART_Mode_Rx; USART_Init(USART1,&uart); USART_Cmd(USART1,ENABLE);
    USART_ITConfig(USART1,USART_IT_RXNE,ENABLE); NVIC_SetPriority(USART1_IRQn,2); NVIC_EnableIRQ(USART1_IRQn);
    DMA_StructInit(&dma); dma.DMA_PeripheralBaseAddr=(uint32_t)&USART1->DR;
    dma.DMA_MemoryBaseAddr=(uint32_t)tx_buffer; dma.DMA_DIR=DMA_DIR_PeripheralDST;
    dma.DMA_BufferSize=64; dma.DMA_MemoryInc=DMA_MemoryInc_Enable;
    dma.DMA_Priority=DMA_Priority_High; DMA_Init(DMA1_Channel4,&dma);
    DMA_ITConfig(DMA1_Channel4,DMA_IT_TC|DMA_IT_TE,ENABLE);
    NVIC_SetPriority(DMA1_Channel4_IRQn,3); NVIC_EnableIRQ(DMA1_Channel4_IRQn);
    USART_DMACmd(USART1,USART_DMAReq_Tx,ENABLE);
    ADC_StructInit(&adc); adc.ADC_Mode=ADC_Mode_Independent;
    adc.ADC_ExternalTrigConv=ADC_ExternalTrigConv_None; adc.ADC_DataAlign=ADC_DataAlign_Right;
    adc.ADC_NbrOfChannel=1; ADC_Init(ADC1,&adc); ADC_Cmd(ADC1,ENABLE); wait_us(10);
    ADC_ResetCalibration(ADC1); while(ADC_GetResetCalibrationStatus(ADC1));
    ADC_StartCalibration(ADC1); while(ADC_GetCalibrationStatus(ADC1));
    ADC_RegularChannelConfig(ADC1,ADC_Channel_0,1,GLOVE_ADC_SAMPLE_TIME);
    TIM_Cmd(TIM3,ENABLE);
}
int main(void) {
    initialize();
    for(;;) {
        uint32_t seq=0, mask=__get_PRIMASK(); uint8_t run;
        __disable_irq(); run=sample_due;
        if(run) { seq=due_seq; sample_due=0; sampling=1; }
        __set_PRIMASK(mask);
        if(run) { acquire(seq); sampling=0; }
        transmit();
    }
}
