// src/screens/economics/panels/RbiPanel.cpp
// RBI data panel — policy rates, forex reserves, money supply, WPI inflation, credit growth.
#include "screens/economics/panels/RbiPanel.h"

#include "core/logging/Logger.h"
#include "services/economics/EconomicsService.h"

#include <QHBoxLayout>
#include <QJsonArray>
#include <QJsonObject>
#include <QLabel>

namespace fincept::screens {
namespace {

static constexpr const char* kRbiScript   = "rbi_data.py";
static constexpr const char* kRbiSourceId = "rbi";
static constexpr const char* kRbiColor    = "#FF6B00"; // saffron

struct RbiSeries {
    QString label;
    QString command;
};

static const QList<RbiSeries> kRbiSeries = {
    {"Policy Rates (Repo / CRR / SLR)",  "policy_rates"},
    {"Forex Reserves (USD bn)",          "forex_reserves"},
    {"Money Supply (M3)",                "money_supply"},
    {"Inflation — WPI",                  "inflation_wpi"},
    {"Bank Credit Growth",               "credit_growth"},
};

} // namespace

RbiPanel::RbiPanel(QWidget* parent) : EconPanelBase(kRbiSourceId, kRbiColor, parent) {
    build_base_ui(this);
    connect(&services::EconomicsService::instance(), &services::EconomicsService::result_ready,
            this, &RbiPanel::on_result);
}

void RbiPanel::activate() {
    show_empty(tr("Select a series and click FETCH\n"
                  "Source: Reserve Bank of India (RBI) public APIs"));
}

void RbiPanel::build_controls(QHBoxLayout* thl) {
    auto lbl = [](const QString& t) {
        auto* l = new QLabel(t);
        l->setStyleSheet(ctrl_label_style());
        return l;
    };

    series_combo_ = new QComboBox;
    for (const auto& s : kRbiSeries)
        series_combo_->addItem(s.label);
    series_combo_->setFixedHeight(26);
    series_combo_->setMinimumWidth(240);

    thl->addWidget(series_lbl_ = lbl(tr("SERIES")));
    thl->addWidget(series_combo_);
}

void RbiPanel::on_fetch() {
    const int idx = series_combo_->currentIndex();
    if (idx < 0 || idx >= kRbiSeries.size())
        return;
    const auto& s = kRbiSeries[idx];
    show_loading(tr("Fetching RBI data: %1…").arg(s.label));
    const QString req_id = "rbi_" + s.command;
    QStringList args = {s.command};
    services::EconomicsService::instance().execute(kRbiSourceId, kRbiScript, s.command, args, req_id);
}

void RbiPanel::on_result(const QString& request_id, const services::EconomicsResult& result) {
    if (result.source_id != kRbiSourceId)
        return;
    if (!result.success) {
        show_error(result.error);
        return;
    }
    if (!request_id.startsWith("rbi_"))
        return;

    // Normalise: prefer "data" array, otherwise wrap top-level object as single row
    QJsonArray rows = result.data["data"].toArray();
    if (rows.isEmpty()) {
        // Try "rates" key (policy_rates response)
        rows = result.data["rates"].toArray();
    }
    if (rows.isEmpty() && !result.data.isEmpty()) {
        // Wrap flat object as a single row
        QJsonObject row;
        for (auto it = result.data.begin(); it != result.data.end(); ++it)
            row[it.key()] = it.value();
        rows.append(row);
    }

    if (rows.isEmpty()) {
        show_error(tr("No data returned from RBI API"));
        return;
    }

    const int idx = series_combo_->currentIndex();
    const QString title = (idx >= 0 && idx < kRbiSeries.size())
                              ? "RBI: " + kRbiSeries[idx].label
                              : "RBI Data";
    display(rows, title);
    LOG_INFO("RbiPanel", QString("Displayed %1 rows for %2").arg(rows.size()).arg(title));
}

void RbiPanel::changeEvent(QEvent* event) {
    if (event->type() == QEvent::LanguageChange)
        retranslateUi();
    EconPanelBase::changeEvent(event);
}

void RbiPanel::retranslateUi() {
    if (series_lbl_) series_lbl_->setText(tr("SERIES"));
    EconPanelBase::retranslateUi();
}

} // namespace fincept::screens
