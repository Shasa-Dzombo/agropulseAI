/*
 * Copyright (c) 2016-2019, Sergey Ryazanov <ryazanov.s.a@gmail.com>
 *
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN

 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

#ifndef _CCRONEXPR_H_
#define _CCRONEXPR_H_

#include <time.h>
#include <stdint.h>

#define CRON_MAX_SECONDS_VALUE 59
#define CRON_MAX_MINUTES_VALUE 59
#define CRON_MAX_HOURS_VALUE 23
#define CRON_MAX_DAYS_OF_WEEK_VALUE 6
#define CRON_MAX_DAYS_OF_MONTH_VALUE 31
#define CRON_MAX_MONTHS_VALUE 12

#define CRON_MIN_SECONDS_VALUE 0
#define CRON_MIN_MINUTES_VALUE 0
#define CRON_MIN_HOURS_VALUE 0
#define CRON_MIN_DAYS_OF_WEEK_VALUE 0
#define CRON_MIN_DAYS_OF_MONTH_VALUE 1
#define CRON_MIN_MONTHS_VALUE 1

#define CRON_ARRAY_SIZE(x) (sizeof(x)/sizeof(x[0]))

typedef struct cron_expr {
	uint8_t seconds[8];
	uint8_t minutes[8];
	uint8_t hours[3];
	uint8_t days_of_week[1];
	uint8_t days_of_month[4];
	uint8_t months[2];
} cron_expr;

extern const char *cron_parse_expr(const char *expression, cron_expr *target, const char **error);

extern time_t cron_next(cron_expr *expr, time_t date);

#endif /* _CCRONEXPR_H_ */
