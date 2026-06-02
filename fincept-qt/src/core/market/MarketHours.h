#pragma once
// MarketHours — session schedule for a named exchange.
//
// All times are stored as minutes-since-midnight in the exchange's local
// timezone. Use MarketHours::for_exchange() to look up a known exchange by
// its MIC/short code (e.g. "NSE", "BSE", "NYSE").
//
// Usage:
//   auto h = MarketHours::for_exchange("NSE");
//   auto status = h.status_now();       // MarketStatus::Open / PreOpen / etc.
//   bool open   = h.is_trading_now();   // true during regular session only

#include <QDateTime>
#include <QTimeZone>
#include <QString>

namespace fincept::market {

enum class MarketStatus {
    PreOpen,      // Pre-open call auction
    Open,         // Regular trading session
    PostClose,    // Post-close / closing session
    Closed,       // Outside all sessions
};

struct Session {
    int start_minutes; // minutes since midnight, local exchange time
    int end_minutes;
};

struct MarketHours {
    QString exchange_code;    // e.g. "NSE"
    QString exchange_name;    // e.g. "National Stock Exchange"
    QTimeZone timezone;       // e.g. QTimeZone("Asia/Kolkata")
    Session pre_open;         // call auction / pre-open session
    Session regular;          // main trading window
    Session post_close;       // post-close / closing call auction

    // Returns local time at the exchange right now.
    QTime local_time() const {
        return QDateTime::currentDateTimeUtc().toTimeZone(timezone).time();
    }

    MarketStatus status_now() const {
        const int now = local_time().hour() * 60 + local_time().minute();
        if (now >= regular.start_minutes && now < regular.end_minutes)
            return MarketStatus::Open;
        if (now >= pre_open.start_minutes && now < pre_open.end_minutes)
            return MarketStatus::PreOpen;
        if (now >= post_close.start_minutes && now < post_close.end_minutes)
            return MarketStatus::PostClose;
        return MarketStatus::Closed;
    }

    bool is_trading_now() const { return status_now() == MarketStatus::Open; }

    static QString status_label(MarketStatus s) {
        switch (s) {
        case MarketStatus::PreOpen:   return QStringLiteral("Pre-Open");
        case MarketStatus::Open:      return QStringLiteral("Market Open");
        case MarketStatus::PostClose: return QStringLiteral("Post-Close");
        case MarketStatus::Closed:    return QStringLiteral("Market Closed");
        }
        return QStringLiteral("Unknown");
    }

    // Lookup by exchange code. Returns NSE schedule for unknown codes.
    static MarketHours for_exchange(const QString& code);
};

// ── Exchange definitions ────────────────────────────────────────────────────

inline MarketHours nse_hours() {
    // NSE/BSE: IST = UTC+5:30
    // Pre-open:  09:00–09:15
    // Regular:   09:15–15:30
    // Post-close:15:40–16:00
    return {
        QStringLiteral("NSE"),
        QStringLiteral("National Stock Exchange of India"),
        QTimeZone("Asia/Kolkata"),
        {9 * 60,       9 * 60 + 15},   // pre-open
        {9 * 60 + 15,  15 * 60 + 30},  // regular
        {15 * 60 + 40, 16 * 60},        // post-close
    };
}

inline MarketHours bse_hours() {
    // BSE mirrors NSE session times exactly
    auto h = nse_hours();
    h.exchange_code = QStringLiteral("BSE");
    h.exchange_name = QStringLiteral("Bombay Stock Exchange");
    return h;
}

inline MarketHours nfo_hours() {
    // NSE F&O (NFO): same as NSE equity but extends to 15:30 (same)
    auto h = nse_hours();
    h.exchange_code = QStringLiteral("NFO");
    h.exchange_name = QStringLiteral("NSE Futures & Options");
    return h;
}

inline MarketHours cds_hours() {
    // NSE Currency Derivatives: 09:00–17:00 IST
    return {
        QStringLiteral("CDS"),
        QStringLiteral("NSE Currency Derivatives"),
        QTimeZone("Asia/Kolkata"),
        {9 * 60,  9 * 60 + 15},
        {9 * 60,  17 * 60},
        {17 * 60, 17 * 60 + 15},
    };
}

inline MarketHours nyse_hours() {
    return {
        QStringLiteral("NYSE"),
        QStringLiteral("New York Stock Exchange"),
        QTimeZone("America/New_York"),
        {9 * 60,       9 * 60 + 30},
        {9 * 60 + 30,  16 * 60},
        {16 * 60,      20 * 60},
    };
}

inline MarketHours MarketHours::for_exchange(const QString& code) {
    if (code == QLatin1String("NSE") || code == QLatin1String("NSE_EQ"))
        return nse_hours();
    if (code == QLatin1String("BSE"))
        return bse_hours();
    if (code == QLatin1String("NFO"))
        return nfo_hours();
    if (code == QLatin1String("CDS"))
        return cds_hours();
    if (code == QLatin1String("NYSE") || code == QLatin1String("NASDAQ"))
        return nyse_hours();
    return nse_hours(); // default to NSE for unknown Indian exchanges
}

} // namespace fincept::market
