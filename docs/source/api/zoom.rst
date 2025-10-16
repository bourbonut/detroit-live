Zoom
====

.. autofunction:: detroit_live.zoom

.. autoclass:: detroit_live.zoom.zoom.Zoom

   .. automethod:: __call__
   .. automethod:: transform
   .. automethod:: scale_by
   .. automethod:: scale_to
   .. automethod:: translate_by
   .. automethod:: translate_to
   .. automethod:: on
   .. automethod:: set_wheel_delta
   .. automethod:: set_filter
   .. automethod:: set_touchable
   .. automethod:: set_extent
   .. automethod:: set_scale_extent
   .. automethod:: set_translate_extent
   .. automethod:: set_constrain
   .. automethod:: set_duration
   .. automethod:: set_interpolate
   .. automethod:: set_click_distance
   .. automethod:: set_tap_distance

Zoom Transform
--------------

.. autofunction:: detroit_live.zoom_transform

.. autoclass:: detroit_live.ZoomTransform
.. autoclass:: detroit_live.zoom_identity

.. note::

   :code:`d3.zoom_identity` is equivalent to :code:`d3.ZoomTransform(1, 0, 0)`

.. autoclass:: detroit_live.zoom.transform.Transform

   .. automethod:: __call__
   .. automethod:: __eq__
   .. automethod:: scale
   .. automethod:: translate
   .. automethod:: apply_x
   .. automethod:: apply_y
   .. automethod:: invert
   .. automethod:: invert_x
   .. automethod:: invert_y
   .. automethod:: __str__
