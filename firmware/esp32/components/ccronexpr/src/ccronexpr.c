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

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>

#include "ccronexpr.h"

#define CRON_MAX_RANGES_PER_FIELD 16
#define CRON_MAX_FIELD_LEN 64

enum cron_field_idx {
	CRON_FIELD_SECONDS,
	CRON_FIELD_MINUTES,
	CRON_FIELD_HOURS,
	CRON_FIELD_DAYS_OF_MONTH,
	CRON_FIELD_MONTHS,
	CRON_FIELD_DAYS_OF_WEEK,
	CRON_FIELD_NB
};

struct cron_field_def {
	const char *name;
	uint8_t min;
	uint8_t max;
	const char *names;
	size_t names_len;
	size_t names_nb;
	size_t range;
};

static const char cron_field_seconds_names[] = "sun\0mon\0tue\0wed\0thu\0fri\0sat";
static const char cron_field_minutes_names[] = "sun\0mon\0tue\0wed\0thu\0fri\0sat";
static const char cron_field_hours_names[] = "sun\0mon\0tue\0wed\0thu\0fri\0sat";
static const char cron_field_days_of_month_names[] = "sun\0mon\0tue\0wed\0thu\0fri\0sat";
static const char cron_field_months_names[] = "jan\0feb\0mar\0apr\0may\0jun\0jul\0aug\0sep\0oct\0nov\0dec";
static const char cron_field_days_of_week_names[] = "sun\0mon\0tue\0wed\0thu\0fri\0sat";

static const struct cron_field_def cron_field_defs[CRON_FIELD_NB] = {
	[CRON_FIELD_SECONDS] = {
		.name = "seconds",
		.min = CRON_MIN_SECONDS_VALUE,
		.max = CRON_MAX_SECONDS_VALUE,
		.names = cron_field_seconds_names,
		.names_len = 4,
		.names_nb = 0,
		.range = CRON_MAX_SECONDS_VALUE - CRON_MIN_SECONDS_VALUE + 1,
	},
	[CRON_FIELD_MINUTES] = {
		.name = "minutes",
		.min = CRON_MIN_MINUTES_VALUE,
		.max = CRON_MAX_MINUTES_VALUE,
		.names = cron_field_minutes_names,
		.names_len = 4,
		.names_nb = 0,
		.range = CRON_MAX_MINUTES_VALUE - CRON_MIN_MINUTES_VALUE + 1,
	},
	[CRON_FIELD_HOURS] = {
		.name = "hours",
		.min = CRON_MIN_HOURS_VALUE,
		.max = CRON_MAX_HOURS_VALUE,
		.names = cron_field_hours_names,
		.names_len = 4,
		.names_nb = 0,
		.range = CRON_MAX_HOURS_VALUE - CRON_MIN_HOURS_VALUE + 1,
	},
	[CRON_FIELD_DAYS_OF_MONTH] = {
		.name = "days of month",
		.min = CRON_MIN_DAYS_OF_MONTH_VALUE,
		.max = CRON_MAX_DAYS_OF_MONTH_VALUE,
		.names = cron_field_days_of_month_names,
		.names_len = 4,
		.names_nb = 0,
		.range = CRON_MAX_DAYS_OF_MONTH_VALUE - CRON_MIN_DAYS_OF_MONTH_VALUE + 1,
	},
	[CRON_FIELD_MONTHS] = {
		.name = "months",
		.min = CRON_MIN_MONTHS_VALUE,
		.max = CRON_MAX_MONTHS_VALUE,
		.names = cron_field_months_names,
		.names_len = 4,
		.names_nb = 12,
		.range = CRON_MAX_MONTHS_VALUE - CRON_MIN_MONTHS_VALUE + 1,
	},
	[CRON_FIELD_DAYS_OF_WEEK] = {
		.name = "days of week",
		.min = CRON_MIN_DAYS_OF_WEEK_VALUE,
		.max = CRON_MAX_DAYS_OF_WEEK_VALUE,
		.names = cron_field_days_of_week_names,
		.names_len = 4,
		.names_nb = 7,
		.range = CRON_MAX_DAYS_OF_WEEK_VALUE - CRON_MIN_DAYS_OF_WEEK_VALUE + 1,
	},
};

static const char *cron_parse_error;

static int cron_str_to_int(const char *str, int *val)
{
	char *endptr;

	errno = 0;
	*val = strtol(str, &endptr, 10);
	if (errno)
		return -1;
	if (endptr == str || *endptr != '\0')
		return -1;

	return 0;
}

static int cron_get_char_pos(const char *str, char ch)
{
	const char *p = strchr(str, ch);

	if (!p)
		return -1;

	return p - str;
}

static int cron_get_field_val_from_name(const char *str,
					const struct cron_field_def *def)
{
	const char *p;
	size_t i;

	for (i = 0; i < def->names_nb; ++i) {
		p = def->names + i * def->names_len;
		if (strncasecmp(str, p, def->names_len - 1) == 0)
			return i + def->min;
	}

	return -1;
}

static int cron_parse_field_range(const char *str, int *from, int *to,
				  const struct cron_field_def *def)
{
	int pos;
	char buf[CRON_MAX_FIELD_LEN];
	int val;

	pos = cron_get_char_pos(str, '-');
	if (pos < 0) {
		if (cron_str_to_int(str, from) != 0) {
			val = cron_get_field_val_from_name(str, def);
			if (val < 0)
				return -1;
			*from = val;
		}
		*to = *from;
		return 0;
	}

	strncpy(buf, str, pos);
	buf[pos] = '\0';
	if (cron_str_to_int(buf, from) != 0) {
		val = cron_get_field_val_from_name(buf, def);
		if (val < 0)
			return -1;
		*from = val;
	}

	strncpy(buf, str + pos + 1, CRON_ARRAY_SIZE(buf) - 1);
	if (cron_str_to_int(buf, to) != 0) {
		val = cron_get_field_val_from_name(buf, def);
		if (val < 0)
			return -1;
		*to = val;
	}

	return 0;
}

static int cron_parse_field(char *str, uint8_t *target,
			    const struct cron_field_def *def)
{
	char *p = str;
	char *p_end = str + strlen(str);
	char *slash;
	int step = 0;
	int from, to, i;
	char buf[CRON_MAX_FIELD_LEN];
	int pos;

	if (strlen(str) == 1 && str[0] == '*') {
		step = 1;
		from = def->min;
		to = def->max;
	} else if ((pos = cron_get_char_pos(str, '/')) >= 0) {
		strncpy(buf, str, pos);
		buf[pos] = '\0';
		if (strlen(buf) == 1 && buf[0] == '*') {
			from = def->min;
			to = def->max;
		} else {
			if (cron_parse_field_range(buf, &from, &to, def) != 0) {
				cron_parse_error = "invalid range";
				return -1;
			}
		}
		if (cron_str_to_int(str + pos + 1, &step) != 0) {
			cron_parse_error = "invalid step value";
			return -1;
		}
	} else {
		step = 0;
	}

	if (step) {
		if (step == 0) {
			cron_parse_error = "step has to be non-zero";
			return -1;
		}
		if (from < def->min || to > def->max || from > to) {
			cron_parse_error = "invalid range";
			return -1;
		}
		for (i = from; i <= to; i += step) {
			if (i < def->min || i > def->max) {
				cron_parse_error = "range out of bounds";
				return -1;
			}
			target[(i - def->min) / 8] |= 1 << ((i - def->min) % 8);
		}
		return 0;
	}

	while (p < p_end) {
		slash = strchr(p, ',');
		if (slash)
			*slash = '\0';

		if (cron_parse_field_range(p, &from, &to, def) != 0) {
			cron_parse_error = "invalid range";
			return -1;
		}

		if (from < def->min || to > def->max || from > to) {
			cron_parse_error = "invalid range";
			return -1;
		}

		for (i = from; i <= to; ++i)
			target[(i - def->min) / 8] |= 1 << ((i - def->min) % 8);

		if (!slash)
			break;
		p = slash + 1;
	}

	return 0;
}

const char *cron_parse_expr(const char *expression, cron_expr *target,
			    const char **error)
{
	const char *p = expression;
	char *p_end;
	char field[CRON_MAX_FIELD_LEN];
	int i, len;
	const struct cron_field_def *defs = cron_field_defs;
	uint8_t *targets[] = {
		target->seconds,
		target->minutes,
		target->hours,
		target->days_of_month,
		target->months,
		target->days_of_week
	};

	if (error)
		*error = NULL;
	cron_parse_error = NULL;

	memset(target, 0, sizeof(*target));

	for (i = 0; i < CRON_FIELD_NB; ++i) {
		p_end = strchr(p, ' ');
		if (!p_end)
			p_end = (char *)p + strlen(p);

		len = p_end - p;
		if (len == 0 || len >= CRON_MAX_FIELD_LEN) {
			if (error)
				*error = "invalid field value";
			return NULL;
		}
		strncpy(field, p, len);
		field[len] = '\0';

		if (cron_parse_field(field, targets[i], &defs[i]) != 0) {
			if (error)
				*error = cron_parse_error;
			return NULL;
		}

		p = p_end + 1;
		if (!*p) {
			if (i != CRON_FIELD_NB - 1) {
				if (error)
					*error = "unexpected end of expression";
				return NULL;
			}
			break;
		}
	}

	return p;
}

static int cron_find_next_set_bit(uint8_t *bits, int from, int to, int *res)
{
	int i;

	for (i = from; i <= to; ++i) {
		if (bits[i / 8] & (1 << (i % 8))) {
			*res = i;
			return 0;
		}
	}

	return -1;
}

static void cron_add_to_field(struct tm *cal, int field, int val)
{
	switch (field) {
	case CRON_FIELD_SECONDS:
		cal->tm_sec += val;
		break;
	case CRON_FIELD_MINUTES:
		cal->tm_min += val;
		break;
	case CRON_FIELD_HOURS:
		cal->tm_hour += val;
		break;
	case CRON_FIELD_DAYS_OF_WEEK:
	case CRON_FIELD_DAYS_OF_MONTH:
		cal->tm_mday += val;
		break;
	case CRON_FIELD_MONTHS:
		cal->tm_mon += val;
		break;
	}

	if (mktime(cal) == -1) {
		/* Normalization failed */
	}
}

static void cron_set_field(struct tm *cal, int field, int val)
{
	switch (field) {
	case CRON_FIELD_SECONDS:
		cal->tm_sec = val;
		break;
	case CRON_FIELD_MINUTES:
		cal->tm_min = val;
		break;
	case CRON_FIELD_HOURS:
		cal->tm_hour = val;
		break;
	case CRON_FIELD_DAYS_OF_MONTH:
		cal->tm_mday = val;
		break;
	case CRON_FIELD_DAYS_OF_WEEK:
		cal->tm_wday = val;
		break;
	case CRON_FIELD_MONTHS:
		cal->tm_mon = val;
		break;
	}

	if (mktime(cal) == -1) {
		/* Normalization failed */
	}
}

static int cron_get_field(struct tm *cal, int field)
{
	switch (field) {
	case CRON_FIELD_SECONDS:
		return cal->tm_sec;
	case CRON_FIELD_MINUTES:
		return cal->tm_min;
	case CRON_FIELD_HOURS:
		return cal->tm_hour;
	case CRON_FIELD_DAYS_OF_MONTH:
		return cal->tm_mday;
	case CRON_FIELD_DAYS_OF_WEEK:
		return cal->tm_wday;
	case CRON_FIELD_MONTHS:
		return cal->tm_mon;
	}

	return -1;
}

static int cron_is_leap_year(int year)
{
	return (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
}

static int cron_get_month_len(int year, int month)
{
	const int mon_day[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};

	if (month != 1)
		return mon_day[month];

	return mon_day[month] + cron_is_leap_year(year + 1900);
}

time_t cron_next(cron_expr *expr, time_t date)
{
	const struct cron_field_def *defs = cron_field_defs;
	uint8_t *targets[] = {
		expr->seconds,
		expr->minutes,
		expr->hours,
		expr->days_of_month,
		expr->months,
		expr->days_of_week
	};
	struct tm cal_buf;
	struct tm *cal = localtime_r(&date, &cal_buf);
	time_t original_date = date;
	int i, res;

	cron_add_to_field(cal, CRON_FIELD_SECONDS, 1);
	date = mktime(cal);

	while (date > original_date) {
		for (i = 0; i < CRON_FIELD_NB; ++i) {
			int from = cron_get_field(cal, i);
			int to = defs[i].max;
			int field_min = defs[i].min;
			int field_max = defs[i].max;
			int month_len;

			if (i == CRON_FIELD_DAYS_OF_MONTH) {
				month_len = cron_get_month_len(cal->tm_year, cal->tm_mon);
				if (to > month_len)
					to = month_len;
			}

			if (cron_find_next_set_bit(targets[i], from - field_min,
						   to - field_min, &res) == 0) {
				if (res + field_min != from) {
					cron_set_field(cal, i, res + field_min);
					for (int j = 0; j < i; j++)
						cron_set_field(cal, j, defs[j].min);
				}
			} else {
				cron_add_to_field(cal, i, 1);
				for (int j = 0; j < i; j++)
					cron_set_field(cal, j, defs[j].min);
				if (cron_find_next_set_bit(targets[i], 0,
							   field_max - field_min,
							   &res) == 0) {
					cron_set_field(cal, i, res + field_min);
				} else {
					return -1;
				}
			}
		}

		if (targets[CRON_FIELD_DAYS_OF_WEEK][(cal->tm_wday - defs[CRON_FIELD_DAYS_OF_WEEK].min) / 8] &
		    (1 << ((cal->tm_wday - defs[CRON_FIELD_DAYS_OF_WEEK].min) % 8))) {
			break;
		}

		for (i = 0; i < CRON_FIELD_NB; ++i)
			cron_set_field(cal, i, cron_get_field(cal, i));
		cron_add_to_field(cal, CRON_FIELD_DAYS_OF_MONTH, 1);
	}

	return mktime(cal);
}
