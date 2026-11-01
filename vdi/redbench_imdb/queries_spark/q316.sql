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
    n.gender IN ('f') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('A5241', 'A5354', 'A6452', 'B4542', 'C6216', 'C6421', 'G4641', 'G6524', 'J232', 'J4136', 'K526', 'L636', 'M625', 'P3256', 'P5252', 'R416', 'S3123', 'S3152', 'S5425', 'T5245')
  )
  AND (
    ci.note IN ('(annotation researcher)', '(as Angel Balangon-Diesta)', '(as Penny Johnson Jerald)', '(associate producer)', '(computer/video playback supervisor)', '(developer)', '(director of photography)', '(producer)', '(production assistant) (uncredited)', '(production assistant)', '(supervising producer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'cinematographer', 'costume designer', 'director', 'editor', 'miscellaneous crew', 'producer', 'production designer', 'writer')
  )
  AND (
    it1.id IN ('31')
  )
