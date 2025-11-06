/**
 * @file web_content.h
 * @brief Contains the embedded HTML, CSS, and JavaScript for the configuration portal.
 *
 * To avoid needing a filesystem for the web server, all web assets are compiled
 * directly into the firmware as C-style string literals.
 */
#ifndef WEB_CONTENT_H
#define WEB_CONTENT_H

// The main HTML page
extern const char index_html_start[] asm("_binary_index_html_start");
extern const char index_html_end[] asm("_binary_index_html_end");

#endif // WEB_CONTENT_H
