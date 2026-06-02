#pragma once
#include <QString>
#include <cmath>

namespace fincept::ui::formatting {

inline QString format_compact_volume(qint64 volume) {
    if (volume <= 0) return "--";
    double v = static_cast<double>(volume);
    if (v >= 1e9) {
        return QString::number(v / 1e9, 'f', 2) + "B";
    } else if (v >= 1e6) {
        return QString::number(v / 1e6, 'f', 2) + "M";
    } else if (v >= 1e3) {
        return QString::number(v / 1e3, 'f', 2) + "K";
    } else {
        return QString::number(volume);
    }
}

// Indian number grouping: 3-2-2-2... (e.g. 1,23,45,678.00)
inline QString format_indian_number(double v) {
    bool negative = v < 0;
    double a = negative ? -v : v;

    qint64 integer_part = static_cast<qint64>(a);
    int paise = static_cast<int>(std::round((a - static_cast<double>(integer_part)) * 100)) % 100;

    QString int_str = QString::number(integer_part);
    QString result;
    if (int_str.length() <= 3) {
        result = int_str;
    } else {
        result = int_str.right(3);
        QString rem = int_str.left(int_str.length() - 3);
        while (rem.length() > 2) {
            result = rem.right(2) + QLatin1Char(',') + result;
            rem = rem.left(rem.length() - 2);
        }
        result = rem + QLatin1Char(',') + result;
    }
    result += QString(".%1").arg(paise, 2, 10, QLatin1Char('0'));
    return negative ? "-" + result : result;
}

// Compact Indian format: Cr (crore=1e7), L (lakh=1e5), K (thousand)
// e.g. 12500000 -> "1.25Cr", 450000 -> "4.50L", 8500 -> "8.5K"
inline QString format_inr_compact(double v) {
    bool negative = v < 0;
    double a = negative ? -v : v;
    const QString prefix = negative ? QStringLiteral("-") : QString();
    if (a >= 1e7)
        return prefix + QString::number(a / 1e7, 'f', 2) + QStringLiteral("Cr");
    if (a >= 1e5)
        return prefix + QString::number(a / 1e5, 'f', 2) + QStringLiteral("L");
    if (a >= 1e3)
        return prefix + QString::number(a / 1e3, 'f', 1) + QStringLiteral("K");
    return prefix + QString::number(static_cast<qint64>(a));
}

// Compact volume for Indian exchanges (Cr/L/K suffixes)
inline QString format_indian_volume(qint64 volume) {
    if (volume <= 0) return QStringLiteral("--");
    return format_inr_compact(static_cast<double>(volume));
}

} // namespace fincept::ui::formatting
