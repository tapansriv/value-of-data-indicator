SELECT distinct(i1.i_product_name)
FROM dfs.`tmp/item.parquet` i1
WHERE i1.i_manufact_id BETWEEN 738 AND 738+40
  AND
    (SELECT count(*) AS item_cnt
     FROM dfs.`tmp/item.parquet` AS item
     WHERE (item.i_manufact = i1.i_manufact
            AND ((item.i_category = 'Women'
                  AND (item.i_color = 'powder'
                       OR item.i_color = 'khaki')
                  AND (item.i_units = 'Ounce'
                       OR item.i_units = 'Oz')
                  AND (item.i_size = 'medium'
                       OR item.i_size = 'extra large'))
                 OR (item.i_category = 'Women'
                     AND (item.i_color = 'brown'
                          OR item.i_color = 'honeydew')
                     AND (item.i_units = 'Bunch'
                          OR item.i_units = 'Ton')
                     AND (item.i_size = 'N/A'
                          OR item.i_size = 'small'))
                 OR (item.i_category = 'Men'
                     AND (item.i_color = 'floral'
                          OR item.i_color = 'deep')
                     AND (item.i_units = 'N/A'
                          OR item.i_units = 'Dozen')
                     AND (item.i_size = 'petite'
                          OR item.i_size = 'petite'))
                 OR (item.i_category = 'Men'
                     AND (item.i_color = 'light'
                          OR item.i_color = 'cornflower')
                     AND (item.i_units = 'Box'
                          OR item.i_units = 'Pound')
                     AND (item.i_size = 'medium'
                          OR item.i_size = 'extra large'))))
       OR (item.i_manufact = i1.i_manufact
           AND ((item.i_category = 'Women'
                 AND (item.i_color = 'midnight'
                      OR item.i_color = 'snow')
                 AND (item.i_units = 'Pallet'
                      OR item.i_units = 'Gross')
                 AND (item.i_size = 'medium'
                      OR item.i_size = 'extra large'))
                OR (item.i_category = 'Women'
                    AND (item.i_color = 'cyan'
                         OR item.i_color = 'papaya')
                    AND (item.i_units = 'Cup'
                         OR item.i_units = 'Dram')
                    AND (item.i_size = 'N/A'
                         OR item.i_size = 'small'))
                OR (item.i_category = 'Men'
                    AND (item.i_color = 'orange'
                         OR item.i_color = 'frosted')
                    AND (item.i_units = 'Each'
                         OR item.i_units = 'Tbl')
                    AND (item.i_size = 'petite'
                         OR item.i_size = 'petite'))
                OR (item.i_category = 'Men'
                    AND (item.i_color = 'forest'
                         OR item.i_color = 'ghost')
                    AND (item.i_units = 'Lb'
                         OR item.i_units = 'Bundle')
                    AND (item.i_size = 'medium'
                         OR item.i_size = 'extra large'))))) > 0
ORDER BY i1.i_product_name
LIMIT 100;

