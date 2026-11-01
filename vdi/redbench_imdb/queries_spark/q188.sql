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
    n.name_pcode_nf IN ('A4251', 'B425', 'C2461', 'E21', 'J2645', 'J345', 'J4242', 'J4632', 'J514', 'L4626', 'L545', 'M3235', 'N626', 'P1262', 'P3621', 'R4163', 'S2463', 'T215', 'T6521', 'Y1515', 'Y1543')
  )
  AND (
    ci.note IN ('(as Jewel)', '(producer)', '(uncredited)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'editor', 'producer')
  )
  AND (
    it1.id IN ('19')
  )
