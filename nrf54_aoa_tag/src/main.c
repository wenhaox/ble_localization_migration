/*
 * Copyright (c) 2021 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 *
 * Modified for u-blox XPLR-AOA-3 (ANT-B10) anchor compatibility.
 * Based on the direction_finding_connectionless_tx sample.
 *
 * The key addition from the C209 tag firmware is the Eddystone-UID
 * advertising payload.  The u-blox anchor's u-locateEmbed firmware
 * filters on the Eddystone namespace 0x4E494E412D4234544147 ("NINA-B4TAG").
 * Without this, the anchor will ignore the tag even though CTE is present.
 * See: https://portal.u-blox.com/s/question/0D5Oj000006M982KAC
 */

#include <zephyr/types.h>
#include <stddef.h>
#include <errno.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/hci_vs.h>
#include <zephyr/bluetooth/direction.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/util.h>

/* Length of CTE in unit of 8[us] */
#define CTE_LEN (0x14U)
/* Number of CTE send in single periodic advertising train event.
 * C209 uses 1 (tradeoff: power vs anchor sample count).
 * The Nordic sample defaulted to 5; we match the C209 for compatibility.
 */
#define PER_ADV_EVENT_CTE_COUNT 1

#define EDDYSTONE_INSTANCE_ID_LEN 6

/*
 * Extended advertising data: Eddystone-UID format.
 *
 * This is the payload the u-blox anchor scans for.  It contains:
 *   - Flags (no BR/EDR)
 *   - Eddystone 16-bit UUID (0xFEAA)
 *   - Eddystone-UID service data:
 *       * Frame type 0x00 (UID)
 *       * TX power byte
 *       * 10-byte namespace: "NINA-B4TAG" (0x4E494E412D4234544147)
 *       * 6-byte instance ID (filled from MAC at runtime)
 *       * 2 reserved bytes
 *
 * The namespace MUST be "NINA-B4TAG" for the u-locateEmbed default filter.
 * The instance ID is derived from the device MAC so each tag is unique.
 */
static uint8_t eddystone_svc_data[] = {
	0xaa, 0xfe,                                     /* Eddystone UUID */
	0x00,                                           /* UID frame type */
	0x00,                                           /* TX Power */
	'N', 'I', 'N', 'A', '-', 'B', '4', 'T', 'A', 'G',  /* Namespace */
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00,            /* Instance (patched) */
	0x00, 0x00                                      /* Reserved */
};

static struct bt_data ad[] = {
	BT_DATA_BYTES(BT_DATA_FLAGS, BT_LE_AD_NO_BREDR),
	BT_DATA_BYTES(BT_DATA_UUID16_ALL, 0xaa, 0xfe),
	BT_DATA(BT_DATA_SVC_DATA16, eddystone_svc_data, sizeof(eddystone_svc_data)),
};

static void adv_sent_cb(struct bt_le_ext_adv *adv,
			struct bt_le_ext_adv_sent_info *info);

const static struct bt_le_ext_adv_cb adv_callbacks = {
	.sent = adv_sent_cb,
};

static struct bt_le_ext_adv *adv_set;

const static struct bt_le_adv_param param =
		BT_LE_ADV_PARAM_INIT(BT_LE_ADV_OPT_EXT_ADV,
				     BT_GAP_ADV_FAST_INT_MIN_2,
				     BT_GAP_ADV_FAST_INT_MAX_2,
				     NULL);

static struct bt_le_ext_adv_start_param ext_adv_start_param = {
	.timeout = 0,
	.num_events = 0,
};

const static struct bt_le_per_adv_param per_adv_param = {
	.interval_min = 32,
    .interval_max = 32,
	.options = BT_LE_ADV_OPT_USE_TX_POWER,
};

#if defined(CONFIG_BT_DF_CTE_TX_AOD)
static uint8_t ant_patterns[] = {0x2, 0x0, 0x5, 0x6, 0x1, 0x4, 0xC, 0x9, 0xE,
				 0xD, 0x8, 0xA};
#endif /* CONFIG_BT_DF_CTE_TX_AOD */

struct bt_df_adv_cte_tx_param cte_params = { .cte_len = CTE_LEN,
					     .cte_count = PER_ADV_EVENT_CTE_COUNT,
#if defined(CONFIG_BT_DF_CTE_TX_AOD)
					     .cte_type = BT_DF_CTE_TYPE_AOD_2US,
					     .num_ant_ids = ARRAY_SIZE(ant_patterns),
					     .ant_ids = ant_patterns
#else
					     .cte_type = BT_DF_CTE_TYPE_AOA,
					     .num_ant_ids = 0,
					     .ant_ids = NULL
#endif /* CONFIG_BT_DF_CTE_TX_AOD */
};

static void adv_sent_cb(struct bt_le_ext_adv *adv,
			struct bt_le_ext_adv_sent_info *info)
{
	printk("Advertiser[%d] %p sent %d\n", bt_le_ext_adv_get_index(adv),
	       adv, info->num_sent);
}

/*
 * Fill the Eddystone instance ID bytes from the device BLE address.
 * Called after bt_enable() so the identity address is available.
 */
static void fill_instance_id_from_mac(void)
{
	bt_addr_le_t addrs[CONFIG_BT_ID_MAX];
	size_t count = CONFIG_BT_ID_MAX;

	bt_id_get(addrs, &count);
	if (count == 0) {
		printk("Warning: no BT identity available\n");
		return;
	}

	uint8_t *inst = &eddystone_svc_data[14]; /* offset of instance ID */

	if (addrs[0].type == BT_ADDR_LE_PUBLIC) {
		for (int i = 0; i < EDDYSTONE_INSTANCE_ID_LEN; i++) {
			inst[i] = addrs[0].a.val[(EDDYSTONE_INSTANCE_ID_LEN - 1) - i];
		}
	} else {
		memcpy(inst, addrs[0].a.val, EDDYSTONE_INSTANCE_ID_LEN);
	}

	char addr_s[BT_ADDR_LE_STR_LEN];
	bt_addr_le_to_str(&addrs[0], addr_s, sizeof(addr_s));
	printk("Device address: %s\n", addr_s);
	printk("Instance ID: %02x%02x%02x%02x%02x%02x\n",
	       inst[0], inst[1], inst[2], inst[3], inst[4], inst[5]);
}

/*
 * +4 dBm via Nordic VS HCI. Needs CONFIG_BT_CTLR_TX_PWR_DYNAMIC_CONTROL=y
 * and must run *after* bt_le_ext_adv_create() with the real adv handle.
 */
static void set_tx_power_for_adv(struct bt_le_ext_adv *adv, int8_t tx_power_dbm)
{
	struct bt_hci_cp_vs_write_tx_power_level *cp;
	struct bt_hci_rp_vs_write_tx_power_level *rp;
	struct net_buf *buf, *rsp = NULL;
	uint8_t adv_handle;
	int err;

	err = bt_hci_get_adv_handle(adv, &adv_handle);
	if (err) {
		printk("bt_hci_get_adv_handle failed (err %d)\n", err);
		return;
	}

	buf = bt_hci_cmd_alloc(K_FOREVER);
	if (!buf) {
		printk("Failed to allocate HCI TX power command buffer\n");
		return;
	}

	cp = net_buf_add(buf, sizeof(*cp));
	cp->handle_type = BT_HCI_VS_LL_HANDLE_TYPE_ADV;
	cp->handle = sys_cpu_to_le16(adv_handle);
	cp->tx_power_level = tx_power_dbm;

	err = bt_hci_cmd_send_sync(BT_HCI_OP_VS_WRITE_TX_POWER_LEVEL, buf, &rsp);
	if (err) {
		printk("Set TX power failed (err %d)\n", err);
		if (rsp) {
			net_buf_unref(rsp);
		}
		return;
	}

	rp = (void *)rsp->data;
	printk("TX power set to %d dBm (adv handle %u)\n", rp->selected_tx_power,
	       adv_handle);
	net_buf_unref(rsp);
}

int main(void)
{
	int err;

	printk("Starting Connectionless Beacon Demo\n");

	/* Initialize the Bluetooth Subsystem */
	printk("Bluetooth initialization...");
	err = bt_enable(NULL);
	if (err) {
		printk("failed (err %d)\n", err);
		return 0;
	}
	printk("success\n");

	/* Patch the Eddystone instance ID with this device's MAC */
	fill_instance_id_from_mac();

	printk("Advertising set create...");
	err = bt_le_ext_adv_create(&param, &adv_callbacks, &adv_set);
	if (err) {
		printk("failed (err %d)\n", err);
		return 0;
	}
	printk("success\n");

	set_tx_power_for_adv(adv_set, 4);

	printk("Set advertising data...");
	err = bt_le_ext_adv_set_data(adv_set, ad, ARRAY_SIZE(ad), NULL, 0);
	if (err) {
		printk("failed (err %d)\n", err);
		return 0;
	}
	printk("success\n");

	printk("Update CTE params...");
	err = bt_df_set_adv_cte_tx_param(adv_set, &cte_params);
	if (err) {
		printk("failed (err %d)\n", err);
		return 0;
	}
	printk("success\n");

	printk("Periodic advertising params set...");
	err = bt_le_per_adv_set_param(adv_set, &per_adv_param);
	if (err) {
		printk("failed (err %d)\n", err);
		return 0;
	}
	printk("success\n");

	printk("Enable CTE...");
	err = bt_df_adv_cte_tx_enable(adv_set);
	if (err) {
		printk("failed (err %d)\n", err);
		return 0;
	}
	printk("success\n");

	printk("Periodic advertising enable...");
	err = bt_le_per_adv_start(adv_set);
	if (err) {
		printk("failed (err %d)\n", err);
		return 0;
	}
	printk("success\n");

	printk("Extended advertising enable...");
	err = bt_le_ext_adv_start(adv_set, &ext_adv_start_param);
	if (err) {
		printk("failed (err %d)\n", err);
		return 0;
	}
	printk("success\n");

	printk("AoA tag running. Anchor should detect namespace NINA-B4TAG.\n");

	return 0;
}
