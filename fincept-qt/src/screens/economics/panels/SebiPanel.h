// src/screens/economics/panels/SebiPanel.h
// SEBI / NSE India — FII/DII flows, bulk deals, block deals, IPO filings.
// Script: sebi_data.py
#pragma once

#include "screens/economics/panels/EconPanelBase.h"

#include <QComboBox>

namespace fincept::screens {

class SebiPanel : public EconPanelBase {
    Q_OBJECT
  public:
    explicit SebiPanel(QWidget* parent = nullptr);
    void activate() override;

  protected:
    void build_controls(QHBoxLayout* thl) override;
    void on_fetch() override;
    void on_result(const QString& request_id, const services::EconomicsResult& result) override;
    void changeEvent(QEvent* event) override;

  private:
    void retranslateUi() override;

    QComboBox* series_combo_ = nullptr;
    QLabel*    series_lbl_   = nullptr;
};

} // namespace fincept::screens
