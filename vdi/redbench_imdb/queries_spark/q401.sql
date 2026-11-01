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
    n.gender IN ('f', 'm')
  )
  AND (
    n.name_pcode_nf IN ('A4521', 'A5416', 'A6453', 'B6516', 'C2563', 'C6421', 'D5235', 'H5243', 'H5634', 'J134', 'J213', 'J2352', 'J2542', 'J6251', 'K6236', 'L2146', 'L423', 'L5645', 'L6525', 'M6343', 'M6362', 'M6523', 'N35', 'P3642')
  )
  AND (
    ci.note IN ('(executive producer)', '(producer)', '(producer: FUNimation)', '(supervising producer)', '(voice: English version)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'director', 'producer')
  )
  AND (
    it1.id IN ('22')
  )
