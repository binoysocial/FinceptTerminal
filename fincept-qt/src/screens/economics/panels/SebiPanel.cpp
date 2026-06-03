// src/screens/economics/panels/SebiPanel.cpp
// SEBI/NSE market participation data: FII/DII flows, bulk deals, block deals, IPOs.
#include "screens/economics/panels/SebiPanel.h"

#include "core/logging/Logger.h"
#include "services/economics/EconomicsService.h"

#include <QHBoxLayout>
#include <QJsonArray>
#include <QJsonObject>
#include <QLabel>

namespace fincept::screens {
namespace {

static constexpr const char* kScript   = "sebi_data.py";
static constexpr const char* kSourceId = "sebi";
static constexpr const char* kColor    = "#138808"; // India green

struct SebiSeries {
    QString label;
    QString command;
};

static const QList<SebiSeries> kSeries = {
    {"FII / DII Daily Flows",       "fii_dii"},
    {"FII / DII Monthly Flows",     "fii_dii_monthly"},
    {"Bulk Deals",                  "bulk_deals"},
    {"Block Deals",                 "block_deals"},
    {"IPO Listings",                "ipo_list"},
    {"Short Selling Data",          "short_selling"},
};

} // namespace

SebiPanel::SebiPanel(QWidget* parent) : EconPanelBase(kSourceId, kColor, parent) {
    build_base_ui(this);
    connect(&services::EconomicsService::instance(), &services::EconomicsService::result_ready,
            this, &SebiPanel::on_result);
}

void SebiPanel::activate() {
    show_empty(tr("Select a dataset and click FETCH\n"
                  "Source: SEBI / NSE public APIs — FII/DII flows, bulk/block deals, IPOs"));
}

void SebiPanel::build_controls(QHBoxLayout* thl) {
    auto lbl = [](const QString& t) {
        auto* l = new QLabel(t);
        l->setStyleSheet(ctrl_label_style());
        return l;
    };

    series_combo_ = new QComboBox;
    for (const auto& s : kSeries)
        series_combo_->addItem(s.label);
    series_combo_->setFixedHeight(26);
    series_combo_->setMinimumWidth(220);

    thl->addWidget(series_lbl_ = lbl(tr("DATASET")));
    thl->addWidget(series_combo_);
}

void SebiPanel::on_fetch() {
    const int idx = series_combo_->currentIndex();
    if (idx < 0 || idx >= kSeries.size())
        return;
    const auto& s = kSeries[idx];
    show_loading(tr("Fetching SEBI data: %1…").arg(s.label));
    const QString req_id = "sebi_" + s.command;
    services::EconomicsService::instance().execute(kSourceId, kScript, s.command, {s.command}, req_id);
}

void SebiPanel::on_result(const QString& request_id, const services::EconomicsResult& result) {
    if (result.source_id != kSourceId)
        return;
    if (!result.success) {
        show_error(result.error);
        return;
    }
    if (!request_id.startsWith("sebi_"))
        return;

    QJsonArray rows = result.data["data"].toArray();
    if (rows.isEmpty() && !result.data.isEmpty()) {
        QJsonObject row;
        for (auto it = result.data.begin(); it != result.data.end(); ++it)
            row[it.key()] = it.value();
        rows.append(row);
    }

    if (rows.isEmpty()) {
        show_error(tr("No data returned from SEBI/NSE API"));
        return;
    }

    const int idx = series_combo_->currentIndex();
    const QString title = (idx >= 0 && idx < kSeries.size())
                              ? "SEBI: " + kSeries[idx].label
                              : "SEBI Data";
    display(rows, title);
    LOG_INFO("SebiPanel", QString("Displayed %1 rows for %2").arg(rows.size()).arg(title));
}

void SebiPanel::changeEvent(QEvent* event) {
    if (event->type() == QEvent::LanguageChange)
        retranslateUi();
    EconPanelBase::changeEvent(event);
}

void SebiPanel::retranslateUi() {
    if (series_lbl_) series_lbl_->setText(tr("DATASET"));
    EconPanelBase::retranslateUi();
}

} // namespace fincept::screens
