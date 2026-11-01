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
    n.gender IN ('f', 'm') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('A5254', 'C5436', 'E1451', 'E162', 'F1626', 'F6524', 'G6231', 'H6315', 'J5426', 'L2152', 'M4261', 'P3525', 'P5451', 'R2416', 'R2526', 'R5323', 'S3126', 'S561')
  )
  AND (
    ci.note IN ('(archive footage)', '(producer)', '(writer)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'director', 'editor', 'producer', 'writer')
  )
  AND (
    it1.id IN ('31')
  )
