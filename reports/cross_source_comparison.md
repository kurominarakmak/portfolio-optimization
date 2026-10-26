# Matched cross-source comparison

**EXPLORATORY_REAL_MARKET / HISTORICAL_RETURN_REPLAY — NO_TRADE.**

Matched valid accounts: 250; unmatched/unavailable valid IDs: []. Same definitions, dates, initial weights and mandate verified before comparisons. Differences are Tiingo minus Alpaca; differing return definitions are retained, not treated as equivalent executable prices.


## buy_hold

| Metric | n | Missing | Mean | Median | p5 | p25 | p75 | p95 | Minimum | Lower-decile mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| net_return_tiingo_minus_alpaca | 250 | 0 | -0.00056145562 | -0.00052145951 | -0.0010170684 | -0.00068295967 | -0.00038302579 | -0.00016014269 | -0.0020105841 | -0.0012424876 |
| es_tiingo_minus_alpaca | 250 | 0 | 3.306859e-05 | 2.8861476e-05 | -5.6874048e-05 | -1.6053915e-06 | 7.1655635e-05 | 0.00012523217 | -0.00015905729 | -7.4863041e-05 |
| mean_forecast_es_difference | 250 | 0 | 3.8363218e-05 | 3.9002843e-05 | -3.4052666e-05 | 1.4683081e-05 | 6.3780372e-05 | 0.00010069476 | -9.0031392e-05 | -3.9608677e-05 |
| mean_absolute_forecast_es_difference | 250 | 0 | 8.0737793e-05 | 7.7689996e-05 | 4.358586e-05 | 6.1978837e-05 | 9.2065892e-05 | 0.0001304896 | 2.6818416e-05 | 4.2457355e-05 |
| mean_forecast_var_difference | 250 | 0 | 3.3492234e-05 | 3.7690182e-05 | -0.00010971058 | -1.5194325e-05 | 8.2868408e-05 | 0.00015756578 | -0.00023297693 | -0.00011558573 |
| mean_fold_allocation_l1_difference | 250 | 0 | 0.00035231654 | 0.00034506395 | 0.00021778482 | 0.00029832687 | 0.00040903263 | 0.00047692237 | 0.00019280809 | 0.00022064649 |
| max_fold_allocation_l1_difference | 250 | 0 | 0.00094603917 | 0.00079588111 | 0.0004449802 | 0.00057688606 | 0.0011907319 | 0.0019416422 | 0.00031779997 | 0.00043829786 |
| rank_difference_tiingo_minus_alpaca | 250 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -2 | -0.24 |

Spearman cumulative-return ranking correlation: 0.99999232.

Portfolio-mean daily return difference -3.4576623e-07; conditional date-block interval [-8.3078386e-06, 7.8259533e-06].


## equal_weight

| Metric | n | Missing | Mean | Median | p5 | p25 | p75 | p95 | Minimum | Lower-decile mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| net_return_tiingo_minus_alpaca | 250 | 0 | -0.00071752357 | -0.00071478881 | -0.0011807604 | -0.00087291526 | -0.00053740649 | -0.00033610337 | -0.0016475777 | -0.0012246618 |
| es_tiingo_minus_alpaca | 250 | 0 | 3.6905082e-05 | 3.7354511e-05 | -2.025685e-05 | 1.2569829e-05 | 6.1693604e-05 | 9.8579501e-05 | -8.3992637e-05 | -2.6484787e-05 |
| mean_forecast_es_difference | 250 | 0 | 4.5273025e-05 | 4.6813101e-05 | 5.2480847e-06 | 2.6306976e-05 | 6.1362314e-05 | 9.2206994e-05 | -4.600834e-05 | -1.7445507e-06 |
| mean_absolute_forecast_es_difference | 250 | 0 | 6.523859e-05 | 6.305964e-05 | 3.5945152e-05 | 5.2306152e-05 | 7.540693e-05 | 9.7968884e-05 | 2.6482793e-05 | 3.580984e-05 |
| mean_forecast_var_difference | 250 | 0 | 4.0196573e-05 | 3.8038815e-05 | -6.9136443e-05 | -2.8697079e-06 | 8.0162617e-05 | 0.00015505047 | -0.00011887952 | -7.3136858e-05 |
| mean_fold_allocation_l1_difference | 250 | 0 | 1.2806445e-11 | 8.0978969e-12 | 2.1017357e-12 | 3.9196662e-12 | 2.1006185e-11 | 3.8311908e-11 | 1.4441593e-12 | 1.9945241e-12 |
| max_fold_allocation_l1_difference | 250 | 0 | 1.0645277e-10 | 5.8715241e-11 | 8.4074844e-12 | 2.0133659e-11 | 1.8901783e-10 | 3.0479612e-10 | 4.5625309e-12 | 7.9940149e-12 |
| rank_difference_tiingo_minus_alpaca | 250 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -2 | -0.52 |

Spearman cumulative-return ranking correlation: 0.99998848.

Portfolio-mean daily return difference -4.2511655e-07; conditional date-block interval [-7.4775803e-06, 6.9430643e-06].


## min_variance

| Metric | n | Missing | Mean | Median | p5 | p25 | p75 | p95 | Minimum | Lower-decile mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| net_return_tiingo_minus_alpaca | 250 | 0 | -0.00020303016 | -0.00022907217 | -0.0026861075 | -0.0012236969 | 0.00084075123 | 0.0026727145 | -0.0058715471 | -0.0030935302 |
| es_tiingo_minus_alpaca | 250 | 0 | 2.3510061e-05 | 2.0871902e-05 | -6.5918456e-05 | -1.5016086e-05 | 6.3072292e-05 | 0.00012047276 | -0.00010100464 | -7.0727063e-05 |
| mean_forecast_es_difference | 250 | 0 | 2.7326968e-05 | 2.8016662e-05 | -4.4790001e-05 | -6.534582e-06 | 6.2048987e-05 | 9.8051516e-05 | -6.7479382e-05 | -4.7609852e-05 |
| mean_absolute_forecast_es_difference | 250 | 0 | 7.0172273e-05 | 6.7398415e-05 | 4.1480716e-05 | 5.492699e-05 | 8.1030594e-05 | 0.00010950052 | 2.869378e-05 | 4.0510693e-05 |
| mean_forecast_var_difference | 250 | 0 | 1.3629127e-05 | 6.9128795e-06 | -0.00010105422 | -3.7494233e-05 | 6.0015463e-05 | 0.000142039 | -0.00022631829 | -0.00011390816 |
| mean_fold_allocation_l1_difference | 250 | 0 | 0.0077525375 | 0.0071635973 | 0.0047478836 | 0.0059468894 | 0.0093552164 | 0.012479914 | 0.0026224825 | 0.0044752796 |
| max_fold_allocation_l1_difference | 250 | 0 | 0.012791899 | 0.011431062 | 0.0074332297 | 0.0095528634 | 0.015292111 | 0.02109012 | 0.0053734069 | 0.0071456331 |
| rank_difference_tiingo_minus_alpaca | 250 | 0 | 0 | 0 | -2 | -1 | 0 | 2 | -4 | -2.44 |

Spearman cumulative-return ranking correlation: 0.99981337.

Portfolio-mean daily return difference -1.7258284e-07; conditional date-block interval [-1.0325879e-05, 1.0674481e-05].


## risk_parity

| Metric | n | Missing | Mean | Median | p5 | p25 | p75 | p95 | Minimum | Lower-decile mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| net_return_tiingo_minus_alpaca | 250 | 0 | -0.00038508424 | -0.00034797878 | -0.0011725807 | -0.00066970194 | -5.7133889e-05 | 0.0003042524 | -0.0019813568 | -0.0012777408 |
| es_tiingo_minus_alpaca | 250 | 0 | 3.0763096e-05 | 3.2443685e-05 | -3.1128392e-05 | 3.334678e-06 | 5.4703368e-05 | 9.5537065e-05 | -6.4405422e-05 | -3.558172e-05 |
| mean_forecast_es_difference | 250 | 0 | 4.1546913e-05 | 3.853965e-05 | -9.5809444e-06 | 1.9349046e-05 | 6.3770385e-05 | 0.00010018674 | -6.0888766e-05 | -1.312067e-05 |
| mean_absolute_forecast_es_difference | 250 | 0 | 6.5139825e-05 | 6.3236662e-05 | 3.9055481e-05 | 4.9726658e-05 | 7.7088562e-05 | 0.00010553506 | 2.1447371e-05 | 3.7446246e-05 |
| mean_forecast_var_difference | 250 | 0 | 3.1118297e-05 | 2.7985004e-05 | -6.4721265e-05 | -1.9025192e-05 | 7.1285568e-05 | 0.00013835727 | -0.00014074122 | -7.6500286e-05 |
| mean_fold_allocation_l1_difference | 250 | 0 | 0.0015738004 | 0.0015691462 | 0.0010622946 | 0.001331523 | 0.0018102634 | 0.0021787121 | 0.00075549243 | 0.0010353772 |
| max_fold_allocation_l1_difference | 250 | 0 | 0.0025159877 | 0.0025263725 | 0.0016266368 | 0.0020832254 | 0.0028801374 | 0.0034788519 | 0.001146614 | 0.0015959687 |
| rank_difference_tiingo_minus_alpaca | 250 | 0 | 0 | 0 | -1 | 0 | 0 | 1 | -3 | -1 |

Spearman cumulative-return ranking correlation: 0.99997312.

Portfolio-mean daily return difference -1.9729633e-07; conditional date-block interval [-8.50582e-06, 8.3767971e-06].


## bl_mv

| Metric | n | Missing | Mean | Median | p5 | p25 | p75 | p95 | Minimum | Lower-decile mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| net_return_tiingo_minus_alpaca | 250 | 0 | -0.00059788043 | -0.00053246883 | -0.0020358543 | -0.00078966586 | -0.00032706875 | 0.00035514228 | -0.0044710114 | -0.002250895 |
| es_tiingo_minus_alpaca | 250 | 0 | 3.2021033e-05 | 3.1818214e-05 | -5.1582193e-05 | -3.2651666e-06 | 6.2552455e-05 | 0.00013388477 | -0.00014906994 | -7.0652223e-05 |
| mean_forecast_es_difference | 250 | 0 | 3.1681894e-05 | 3.1633843e-05 | -3.5133538e-05 | 9.2543005e-06 | 5.7684551e-05 | 9.2683551e-05 | -0.00011855234 | -4.2484405e-05 |
| mean_absolute_forecast_es_difference | 250 | 0 | 7.4939224e-05 | 7.2621719e-05 | 4.2116645e-05 | 5.8769998e-05 | 8.8128091e-05 | 0.00011870651 | 2.8635216e-05 | 4.0244529e-05 |
| mean_forecast_var_difference | 250 | 0 | 3.5569196e-05 | 3.1167991e-05 | -0.00010125826 | -2.2767595e-05 | 8.659798e-05 | 0.00018875157 | -0.00023798183 | -0.00011008586 |
| mean_fold_allocation_l1_difference | 250 | 0 | 0.0011618466 | 0.00044115026 | 0.00025827232 | 0.0003274296 | 0.0012617036 | 0.0040114189 | 0.00020787962 | 0.00025031252 |
| max_fold_allocation_l1_difference | 250 | 0 | 0.0021214915 | 0.0011500692 | 0.00050368403 | 0.00065533879 | 0.0026988678 | 0.0060418579 | 0.00036800608 | 0.00048669961 |
| rank_difference_tiingo_minus_alpaca | 250 | 0 | 0 | 0 | -1 | 0 | 0 | 1 | -2 | -0.96 |

Spearman cumulative-return ranking correlation: 0.99997773.

Portfolio-mean daily return difference -3.9553685e-07; conditional date-block interval [-8.4031143e-06, 7.6614436e-06].


## min_cvar

| Metric | n | Missing | Mean | Median | p5 | p25 | p75 | p95 | Minimum | Lower-decile mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| net_return_tiingo_minus_alpaca | 250 | 0 | -7.7341101e-05 | -0.00073909582 | -0.026858903 | -0.011610886 | 0.011609148 | 0.030332225 | -0.060042806 | -0.031890912 |
| es_tiingo_minus_alpaca | 250 | 0 | 5.7166643e-06 | 9.0881627e-06 | -0.00028480448 | -9.8101623e-05 | 0.00010302534 | 0.00027518378 | -0.00070947333 | -0.00030735327 |
| mean_forecast_es_difference | 250 | 0 | 2.5142436e-05 | 2.4970243e-05 | -4.7324402e-05 | -7.9262332e-06 | 5.5561306e-05 | 0.00010153546 | -9.2035491e-05 | -5.1348793e-05 |
| mean_absolute_forecast_es_difference | 250 | 0 | 8.5527857e-05 | 8.1515186e-05 | 5.1540102e-05 | 6.6743723e-05 | 0.00010345921 | 0.00012960396 | 4.2878877e-05 | 5.065234e-05 |
| mean_forecast_var_difference | 250 | 0 | 1.2732523e-05 | 1.6259561e-05 | -0.00012784477 | -3.5545306e-05 | 6.3994806e-05 | 0.00015562846 | -0.0002954219 | -0.00015178858 |
| mean_fold_allocation_l1_difference | 250 | 0 | 0.04851419 | 0.044220921 | 0.022017983 | 0.034214117 | 0.055507701 | 0.093247247 | 0.015756573 | 0.021746911 |
| max_fold_allocation_l1_difference | 250 | 0 | 0.11146125 | 0.099943497 | 0.048064702 | 0.075727474 | 0.13509293 | 0.19502714 | 0.035694315 | 0.047030687 |
| rank_difference_tiingo_minus_alpaca | 250 | 0 | 0 | 0 | -14 | -5 | 5 | 14 | -32 | -16.24 |

Spearman cumulative-return ranking correlation: 0.99242586.

Portfolio-mean daily return difference 1.5881313e-08; conditional date-block interval [-1.0798241e-05, 1.1150113e-05].


## bl_cvar

| Metric | n | Missing | Mean | Median | p5 | p25 | p75 | p95 | Minimum | Lower-decile mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| net_return_tiingo_minus_alpaca | 250 | 0 | -7.7341103e-05 | -0.00073909582 | -0.026858903 | -0.011610886 | 0.011609148 | 0.030332225 | -0.060042806 | -0.031890912 |
| es_tiingo_minus_alpaca | 250 | 0 | 5.7166644e-06 | 9.0881627e-06 | -0.00028480448 | -9.8101623e-05 | 0.00010302534 | 0.00027518378 | -0.00070947333 | -0.00030735327 |
| mean_forecast_es_difference | 250 | 0 | 2.5142436e-05 | 2.4970243e-05 | -4.7324402e-05 | -7.9262332e-06 | 5.5561306e-05 | 0.00010153546 | -9.2035491e-05 | -5.1348793e-05 |
| mean_absolute_forecast_es_difference | 250 | 0 | 8.5527857e-05 | 8.1515186e-05 | 5.1540102e-05 | 6.6743723e-05 | 0.00010345921 | 0.00012960396 | 4.2878877e-05 | 5.065234e-05 |
| mean_forecast_var_difference | 250 | 0 | 1.2732523e-05 | 1.6259561e-05 | -0.00012784477 | -3.5545306e-05 | 6.3994806e-05 | 0.00015562846 | -0.0002954219 | -0.00015178858 |
| mean_fold_allocation_l1_difference | 250 | 0 | 0.04851419 | 0.044220921 | 0.022017983 | 0.034214117 | 0.055507701 | 0.093247247 | 0.015756573 | 0.021746911 |
| max_fold_allocation_l1_difference | 250 | 0 | 0.11146125 | 0.099943497 | 0.048064702 | 0.075727474 | 0.13509293 | 0.19502714 | 0.035694315 | 0.047030687 |
| rank_difference_tiingo_minus_alpaca | 250 | 0 | 0 | 0 | -14 | -5 | 5 | 14 | -32 | -16.24 |

Spearman cumulative-return ranking correlation: 0.99242586.

Portfolio-mean daily return difference 1.588131e-08; conditional date-block interval [-1.0798241e-05, 1.1150113e-05].


Mean/max fold L1 differences compare matched normalized post-cost allocations. Forecast ES/VaR differences use matched daily exposures and dates. Ranking uses average ranks for ties. No source is declared correct merely because its outcome is better. Date-block intervals use 500 draws, block length10, seed42; multiple comparisons unadjusted. Both sources share selected survivors, local identity assumptions and full-window coverage selection bias.
