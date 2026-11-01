SELECT
  COUNT(*)
FROM name AS n, aka_name AS an, info_type AS it1, person_info AS pi1, cast_info AS ci, role_type AS rt
WHERE
  n.id = ci.person_id
  AND ci.person_id = pi1.person_id
  AND it1.id = pi1.info_type_id
  AND n.id = pi1.person_id
  AND n.id = an.person_id
  AND ci.person_id = an.person_id
  AND an.person_id = pi1.person_id
  AND rt.id = ci.role_id
  AND (
    n.gender IN ('f')
  )
  AND (
    n.name_pcode_nf IN ('A3435', 'C6456', 'G6516', 'H3262', 'J464', 'K3452', 'K4124', 'L651', 'M6165', 'N2163', 'P363', 'S246', 'T2616', 'T51')
  )
  AND (
    ci.note IN ('(head writer)', '(producer)', '(puppeteer: "Salem")', '(uncredited)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('26')
  )
